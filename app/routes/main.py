from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.supabase_client import get_supabase
from app.services.bounty import (
    cell_ids_around, draw_bounties, haversine_km, is_open_now,
    get_level_info, today_header, get_grade, is_hidden_gem,
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
    import hashlib
    user_id = session['user_id']
    sb = get_supabase()

    hunts = sb.table('hunts').select('exp_gained, district').eq('user_id', user_id).execute().data
    total_exp = sum(h['exp_gained'] for h in hunts)
    hunt_count = len(hunts)
    level_info = get_level_info(total_exp)

    district_counts: dict[str, int] = {}
    for h in hunts:
        if h['district']:
            district_counts[h['district']] = district_counts.get(h['district'], 0) + 1

    titles = []
    for d, c in sorted(district_counts.items(), key=lambda x: -x[1]):
        if c >= 25:
            titles.append(f'{d}制霸者')
        elif c >= 10:
            titles.append(f'{d}地頭蛇')

    license_no = f"TW-2026-{hashlib.md5(user_id.encode()).hexdigest()[:6].upper()}"

    return render_template('tavern.html',
        display_name=session['display_name'],
        level_info=level_info,
        hunt_count=hunt_count,
        titles=titles,
        license_no=license_no,
    )


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

    # Fetch from Places API if this cell is stale (no-op if cached or no key)
    if mode == 'explore':
        from app.services.places import ensure_shops_fetched
        ensure_shops_fetched(center_lat, center_lng)

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

    # Level info
    exp_rows = sb.table('hunts').select('exp_gained').eq('user_id', user_id).execute().data
    total_exp = sum(h['exp_gained'] for h in exp_rows)
    level_info = get_level_info(total_exp)

    return render_template('board.html',
        mode=mode,
        state=state,
        bounties=bounties,
        all_hunted_ids=all_hunted_ids,
        sleeping_count=len(closed_shops),
        origin_key=origin_key,
        district=district,
        lat=lat, lng=lng,
        level_info=level_info,
        date_header=today_header(),
        display_name=session['display_name'],
    )


@bp.route('/bounty/<shop_id>')
@login_required
def bounty(shop_id):
    grade = request.args.get('grade', 'C')
    origin_key = request.args.get('origin', '')

    sb = get_supabase()
    shop = sb.table('shops').select('*').eq('id', shop_id).maybe_single().execute().data
    if not shop:
        return redirect(url_for('main.tavern'))

    user_id = session['user_id']
    prev_visits = sb.table('hunts').select('id').eq('user_id', user_id).eq('shop_id', shop_id).execute().data
    visit_count = len(prev_visits)

    _, base_reward = get_grade(shop.get('rating'))
    gem = is_hidden_gem(shop.get('rating'), shop.get('rating_count'))
    multiplier = (2 if gem else 1) * (0.3 if visit_count >= 1 else 1)
    expected_exp = round(base_reward * multiplier)

    return render_template('bounty_detail.html',
        shop=shop,
        grade=grade,
        origin_key=origin_key,
        visit_count=visit_count,
        is_hidden_gem=gem,
        expected_exp=expected_exp,
        display_name=session['display_name'],
    )


@bp.route('/bounty/<shop_id>/complete', methods=['POST'])
@login_required
def complete_bounty(shop_id):
    user_id = session['user_id']
    sb = get_supabase()

    grade = request.form.get('grade', 'C')
    origin_key = request.form.get('origin_key', '')
    player_rating = request.form.get('player_rating', type=int)
    review_text = request.form.get('review_text', '').strip() or None

    shop = sb.table('shops').select('*').eq('id', shop_id).maybe_single().execute().data
    if not shop:
        return redirect(url_for('main.tavern'))

    # Double-submit guard: same user+shop within 1 minute → ignore
    one_min_ago = (datetime.now(TZ) - timedelta(minutes=1)).isoformat()
    if sb.table('hunts').select('id').eq('user_id', user_id).eq('shop_id', shop_id).gte('completed_at', one_min_ago).execute().data:
        return redirect(url_for('main.tavern'))

    # revisit count queried at completion time
    prev_visits = sb.table('hunts').select('id').eq('user_id', user_id).eq('shop_id', shop_id).execute().data
    visit_count = len(prev_visits)

    _, base_reward = get_grade(shop.get('rating'))
    gem = is_hidden_gem(shop.get('rating'), shop.get('rating_count'))
    multiplier = (2 if gem else 1) * (0.3 if visit_count >= 1 else 1)
    exp_gained = round(base_reward * multiplier)

    # Capture level before insert
    exp_rows = sb.table('hunts').select('exp_gained').eq('user_id', user_id).execute().data
    total_exp_before = sum(h['exp_gained'] for h in exp_rows)
    level_before = get_level_info(total_exp_before)

    sb.table('hunts').insert({
        'user_id': user_id,
        'shop_id': shop_id,
        'exp_gained': exp_gained,
        'player_rating': player_rating,
        'review_text': review_text,
        'district': shop.get('district'),
    }).execute()

    level_after = get_level_info(total_exp_before + exp_gained)

    session['last_hunt'] = {
        'shop_name': shop['name'],
        'shop_district': shop.get('district') or '',
        'grade': grade,
        'exp_gained': exp_gained,
        'is_hidden_gem': gem,
        'is_revisit': visit_count >= 1,
        'leveled_up': level_after['level'] > level_before['level'],
        'level_info': level_after,
    }

    return redirect(url_for('main.hunt_result'))


@bp.route('/result')
@login_required
def hunt_result():
    last = session.pop('last_hunt', None)
    if not last:
        return redirect(url_for('main.tavern'))
    return render_template('hunt_result.html',
        last=last,
        display_name=session['display_name'],
    )


# ---- stubs ----

@bp.route('/expedition')
@login_required
def expedition():
    return '遠征選區（施工中）', 200


@bp.route('/dex')
@login_required
def dex():
    return '圖鑑（施工中）', 200


@bp.route('/dex/<shop_id>')
@login_required
def dex_shop(shop_id):
    return f'圖鑑單頁 {shop_id}（施工中）', 200
