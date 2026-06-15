"""
Google Places API (New) fetcher.
Checks fetch_log before calling the API; fails silently so the board
can still render from cached data if the API is unreachable.
"""
import os
import re
from datetime import datetime, timezone

import requests

from app.supabase_client import get_supabase

_NEARBY_URL = 'https://places.googleapis.com/v1/places:searchNearby'
_FIELD_MASK = ','.join([
    'places.id',
    'places.displayName',
    'places.formattedAddress',
    'places.location',
    'places.rating',
    'places.userRatingCount',
    'places.regularOpeningHours',
])


def _cell_id(lat: float, lng: float) -> str:
    return f"{round(lat, 2)}_{round(lng, 2)}"


def _extract_district(address: str | None) -> str | None:
    if not address:
        return None
    m = re.search(r'(?:台南市|臺南市)(\S+區)', address)
    return m.group(1) if m else None


def _convert_hours(raw: dict | None) -> dict | None:
    """Convert Places API (New) regularOpeningHours to our JSONB schema.

    New API uses {day, hour, minute}; our is_open_now() expects {day, time:'HHMM'}.
    """
    if not raw:
        return None
    periods_in = raw.get('periods', [])
    if not periods_in:
        return None

    converted = []
    for p in periods_in:
        o = p.get('open')
        c = p.get('close')
        if not o:
            continue
        entry = {
            'open': {
                'day': o.get('day', 0),
                'time': f"{o.get('hour', 0):02d}{o.get('minute', 0):02d}",
            },
        }
        if c:
            entry['close'] = {
                'day': c.get('day', 0),
                'time': f"{c.get('hour', 23):02d}{c.get('minute', 59):02d}",
            }
        else:
            # 24-hour: no close entry — treat as unknown to be safe
            continue
        converted.append(entry)

    return {'periods': converted} if converted else None


def ensure_shops_fetched(center_lat: float, center_lng: float) -> None:
    """Fetch nearby restaurants from Places API if the center cell is stale.

    Silently returns on any error so the board still renders from cached shops.
    """
    api_key = os.environ.get('GOOGLE_PLACES_API_KEY')
    if not api_key:
        return

    cell = _cell_id(center_lat, center_lng)
    sb = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Skip if cached within 30 days
    fresh = sb.table('fetch_log').select('id').eq('cell_id', cell).gt('expires_at', now_iso).execute().data
    if fresh:
        return

    try:
        resp = requests.post(
            _NEARBY_URL,
            json={
                'includedTypes': ['restaurant', 'cafe', 'bakery', 'bar'],
                'maxResultCount': 20,
                'rankPreference': 'POPULARITY',
                'languageCode': 'zh-TW',
                'locationRestriction': {
                    'circle': {
                        'center': {'latitude': center_lat, 'longitude': center_lng},
                        'radius': 1500.0,
                    }
                },
            },
            headers={
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': _FIELD_MASK,
            },
            timeout=8,
        )
        resp.raise_for_status()
        places = resp.json().get('places', [])
    except Exception:
        return  # fail silently; board renders from whatever is in DB

    upserted = 0
    for p in places:
        loc = p.get('location') or {}
        lat = loc.get('latitude')
        lng = loc.get('longitude')
        if lat is None or lng is None:
            continue

        name = (p.get('displayName') or {}).get('text') or ''
        if not name:
            continue

        address = p.get('formattedAddress') or ''
        sb.table('shops').upsert({
            'place_id': p['id'],
            'name': name,
            'address': address,
            'district': _extract_district(address),
            'lat': lat,
            'lng': lng,
            'rating': p.get('rating'),
            'rating_count': p.get('userRatingCount'),
            'cell_id': _cell_id(lat, lng),
            'opening_hours': _convert_hours(p.get('regularOpeningHours')),
            'opening_hours_fetched_at': now_iso,
            'source': 'places_api',
        }, on_conflict='place_id').execute()
        upserted += 1

    sb.table('fetch_log').insert({
        'cell_id': cell,
        'shop_count': upserted,
    }).execute()
