import hashlib
import math
import random
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Taipei')

_GRADES = [('S', 4.6, 50), ('A', 4.2, 40), ('B', 3.8, 30), ('C', 0.0, 60)]


def get_grade(rating):
    if rating is None:
        return 'C', 60
    for grade, threshold, reward in _GRADES:
        if float(rating) >= threshold:
            return grade, reward
    return 'C', 60


def is_hidden_gem(rating, rating_count):
    return (rating is not None and float(rating) >= 4.5 and
            rating_count is not None and int(rating_count) < 100)


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def cell_ids_around(lat, lng):
    base_lat = round(lat, 2)
    base_lng = round(lng, 2)
    step = 0.01
    return [
        f"{round(base_lat + dlat, 2)}_{round(base_lng + dlng, 2)}"
        for dlat in (-step, 0, step)
        for dlng in (-step, 0, step)
    ]


def is_open_now(opening_hours, now=None):
    """
    Returns True (open), False (closed), None (data unknown).
    Google Places periods: day 0=Sun, 1=Mon … 6=Sat; time "HHMM".
    """
    if not opening_hours:
        return None
    periods = opening_hours.get('periods', [])
    if not periods:
        return None

    if now is None:
        now = datetime.now(TZ)

    # Python weekday(): 0=Mon … 6=Sun → Google: 0=Sun 1=Mon … 6=Sat
    google_day = (now.weekday() + 1) % 7
    prev_day = (google_day - 1) % 7
    cur_min = now.hour * 60 + now.minute

    def t(time_str):
        return int(time_str[:2]) * 60 + int(time_str[2:])

    for p in periods:
        o = p.get('open', {})
        c = p.get('close', {})
        od = o.get('day')
        cd = c.get('day')
        ot = t(o.get('time', '0000'))
        ct = t(c.get('time', '2359'))

        if od == cd == google_day:
            if ot <= cur_min <= ct:
                return True
        elif od == google_day and cd != google_day:
            # opens today, closes next day (overnight)
            if cur_min >= ot:
                return True
        elif cd == google_day and od == prev_day:
            # opened yesterday, closes today
            if cur_min <= ct:
                return True

    return False


def draw_bounties(shops, user_id, origin_key, exclude_ids, count=3):
    """
    Seed-based draw. exclude_ids = shop IDs hunted within 7 days.
    Returns list of dicts: {shop, grade, base_reward, is_hidden_gem}.
    """
    today = datetime.now(TZ).strftime('%Y-%m-%d')
    rng = random.Random(f"{user_id}_{today}_{origin_key}")
    pool = [s for s in shops if s['id'] not in exclude_ids]
    rng.shuffle(pool)

    result = []
    for shop in pool[:count]:
        grade, base_reward = get_grade(shop.get('rating'))
        gem = is_hidden_gem(shop.get('rating'), shop.get('rating_count'))
        result.append({
            'shop': shop,
            'grade': grade,
            'base_reward': base_reward,
            'is_hidden_gem': gem,
            'display_exp': base_reward * (2 if gem else 1),
        })
    return result
