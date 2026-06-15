import os
import secrets
from urllib.parse import urlencode

import requests
from flask import Blueprint, redirect, render_template, request, session, url_for

from app.supabase_client import get_supabase

bp = Blueprint('auth', __name__)

_LINE_AUTH_URL = 'https://access.line.me/oauth2/v2.1/authorize'
_LINE_TOKEN_URL = 'https://api.line.me/oauth2/v2.1/token'
_LINE_PROFILE_URL = 'https://api.line.me/v2/profile'


def _build_line_auth_url() -> str:
    callback_url = os.environ.get('LINE_CALLBACK_URL')
    if not callback_url:
        raise RuntimeError('LINE_CALLBACK_URL is not set. Add it to your environment variables.')
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    return _LINE_AUTH_URL + '?' + urlencode({
        'response_type': 'code',
        'client_id': os.environ['LINE_CHANNEL_ID'],
        'redirect_uri': callback_url,
        'state': state,
        'scope': 'profile openid',
    })


@bp.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('main.tavern'))
    return render_template('login.html', auth_url=_build_line_auth_url())


@bp.route('/callback')
def callback():
    # CSRF: state must be present, match the one we issued, and is single-use.
    # Fail closed if no state was stored (don't let a missing/empty state pass).
    expected_state = session.pop('oauth_state', None)
    given_state = request.args.get('state')
    if request.args.get('error') or not expected_state or given_state != expected_state:
        return redirect(url_for('auth.login'))

    token = _exchange_code(request.args.get('code', ''))
    if not token:
        return redirect(url_for('auth.login'))

    profile = _get_profile(token['access_token'])
    if not profile:
        return redirect(url_for('auth.login'))

    user_id = profile['userId']
    display_name = profile.get('displayName', '')
    sb = get_supabase()

    existing = sb.table('users').select('id').eq('id', user_id).maybe_single().execute()
    is_new_user = existing.data is None

    sb.table('users').upsert({
        'id': user_id,
        'display_name': display_name,
        'picture_url': profile.get('pictureUrl'),
    }, on_conflict='id').execute()

    session['user_id'] = user_id
    session['display_name'] = display_name
    session['welcome'] = {'is_new': is_new_user, 'name': display_name}
    return redirect(url_for('main.welcome'))


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


def _exchange_code(code: str) -> dict | None:
    try:
        r = requests.post(_LINE_TOKEN_URL, data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': os.environ['LINE_CALLBACK_URL'],
            'client_id': os.environ['LINE_CHANNEL_ID'],
            'client_secret': os.environ['LINE_CHANNEL_SECRET'],
        }, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _get_profile(access_token: str) -> dict | None:
    try:
        r = requests.get(_LINE_PROFILE_URL,
                         headers={'Authorization': f'Bearer {access_token}'},
                         timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None
