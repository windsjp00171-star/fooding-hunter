from functools import wraps

from flask import Blueprint, redirect, render_template, session, url_for

bp = Blueprint('main', __name__)


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


# ---- stubs（骨架佔位，後續 session 實作）----

@bp.route('/expedition')
@login_required
def expedition():
    return '遠征選區（施工中）', 200


@bp.route('/board')
@login_required
def board():
    return '懸賞板（施工中）', 200


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
