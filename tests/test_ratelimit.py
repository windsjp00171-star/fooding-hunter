"""Rate limiter returns 429 once the per-window call count is exceeded."""
from flask import Flask

from app.services.ratelimit import rate_limit, _hits


def _make_app():
    app = Flask(__name__)

    @app.route('/x')
    @rate_limit(max_calls=3, per_seconds=60)
    def x():
        return 'ok', 200

    return app


def test_blocks_after_limit():
    _hits.clear()
    app = _make_app()
    client = app.test_client()
    # first 3 allowed
    for _ in range(3):
        assert client.get('/x').status_code == 200
    # 4th within the window is throttled
    assert client.get('/x').status_code == 429
