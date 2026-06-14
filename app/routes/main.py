from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.supabase_client import get_supabase
from app.services.bounty import (
    cell_ids_around, draw_bounties, haversine_km, is_open_now
)

bp = Blueprint('main', __name__)
TZ = ZoneInfo('Asia/Taipei')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@bp.route('/')
@login_required
def tavern():
    return render_template('tavern.html', display_name=session['display_name'])


@bp.route('/board')
@login_required
def board():
    mode = request.args.get('mode', 'explore')
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)

    # explore: wait for GPS if no coords yet
    if mode == 'explore' and (lat is None or lng is None):
        return render_template('board_gps.html')

    # expedition: district required
    district = request.args.get('district')
    if mode == 'expedition' and not district:
        return redirect(url_for('main.expedition'))

    user_id = session['user_id']

    # Determine center and origin_key
    if mode == 'explore':
        center_lat, center_lng = lat, lng
        origin_key = f"{round(lat, 2)}_{round(lng, 2)}"
        radius_km = 1.5
    else:
        from app.tainan_districts import DISTRICTS
        if district not in DISTRICTS:
            return redirect(url_for('main.expedition'))
        center_lat, center_lng = DISTRICTS[district]
        origin_key = district
        radius_km = 2.5

    # Query shops in surrounding cells
    sb = get_supabase()
    cells = cell_ids_around(center_lat, center_lng)
    shops = sb.table('shops').select('*').in_('cell_id', cells).execute().data

    # Haversine filter
    shops = [s for s in shops
             if haversine_km(center_lat, center_lng, s['lat'], s['lng']) <= radius_km]

    # Opening hours filter
    now = datetime.now(TZ)
    open_shops, unknown_shops, closed_shops = [], [], []
    for shop in shops:
        status = is_open_now(shop.get('opening_hours'), now)
        if status is True:
            open_shops.append(shop)
        elif status is None:
            shop['opening_unknown'] = True
            unknown_shops.append(shop)
        else:
            closed_shops.append(shop)

    available = open_shops + unknown_shops

    # Get user's hunt history
    seven_ago = (datetime.now(TZ) - timedelta(days=7)).isoformat()
    recent = sb.table('hunts').select('shop_id').eq('user_id', user_id).gte('completed_at', seven_ago).execute().data
    exclude_ids = {h['shop_id'] for h in recent}

    all_hunted = sb.table('hunts').select('shop_id').eq('user_id', user_id).execute().data
    all_hunted_ids = {h['shop_id'] for h in all_hunted}

    # Draw
    bounties = draw_bounties(available, user_id, origin_key, exclude_ids, count=3)

    # Four-state logic
    if not shops:
        state = 'desolate'
    elif not available:
        state = 'sleeping'
    elif len(bounties) < 3:
        state = 'border'
    else:
        state = 'normal'

    return render_template('board.html',
        mode=mode,
        state=state,
        bounties=bounties,
        all_hunted_ids=all_hunted_ids,
        sleeping_count=len(closed_shops),
        origin_key=origin_key,
        district=district,
        lat=lat, lng=lng,
    )


# ---- stubs ----

@bp.route('/expedition')
@login_required
def expedition():
    return '遠征選區（施工中）', 200


@bp.route('/bounty/<bounty_id>')
@login_required
def bounty(bounty_id):
    return f'懸賞詳情 {bounty_id}（施工中）', 200


@bp.route('/dex')
@login_required
def dex():
    return '圖鑑（施工中）', 200


@bp.route('/dex/<shop_id>')
@login_required
def dex_shop(shop_id):
    return f'圖鑑單頁 {shop_id}（施工中）', 200
