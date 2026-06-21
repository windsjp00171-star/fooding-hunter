import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    app.secret_key = os.environ['FLASK_SECRET_KEY']

    is_prod = os.environ.get('FLASK_ENV') == 'production'

    # Session cookie hardening.
    # - HttpOnly: JS can't read the session cookie (mitigates token theft via XSS)
    # - SameSite=Lax: browser drops the cookie on cross-site POST, which blocks
    #   CSRF on state-changing endpoints (/complete, /board/reroll) while still
    #   sending it on the top-level GET redirect back from LINE OAuth.
    # - Secure: HTTPS-only in production (left off locally so http://localhost works)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=is_prod,
    )

    from .routes import auth, main
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)

    return app
