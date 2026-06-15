"""
Unit tests for daily reroll mechanic:
- draw_bounties seed shifts with reroll_used (different set, but stable per count)
- _reroll_quota: limit = level, resets on day change (Asia/Taipei)
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.bounty import draw_bounties
from app.routes.main import _reroll_quota

TZ = ZoneInfo('Asia/Taipei')


def _shops(n):
    return [
        {'id': f's{i}', 'name': f'店{i}', 'rating': 4.0, 'rating_count': 200,
         'district': '中西區'}
        for i in range(n)
    ]


def test_reroll_changes_draw():
    shops = _shops(12)
    a = [b['shop']['id'] for b in draw_bounties(shops, 'u1', 'cell', set(), reroll_used=0)]
    b = [b['shop']['id'] for b in draw_bounties(shops, 'u1', 'cell', set(), reroll_used=1)]
    assert a != b, "reroll should produce a different set"


def test_reroll_stable_per_count():
    shops = _shops(12)
    a = [x['shop']['id'] for x in draw_bounties(shops, 'u1', 'cell', set(), reroll_used=2)]
    b = [x['shop']['id'] for x in draw_bounties(shops, 'u1', 'cell', set(), reroll_used=2)]
    assert a == b, "same reroll count must be deterministic"


def test_reroll_excludes_recent():
    shops = _shops(12)
    exclude = {'s0', 's1', 's2'}
    for used in range(4):
        ids = {x['shop']['id'] for x in draw_bounties(shops, 'u1', 'cell', exclude, reroll_used=used)}
        assert not (ids & exclude), "7-day excluded shops must never appear in any reroll"


def test_quota_limit_equals_level():
    today = datetime.now(TZ).date().isoformat()
    # level 1 → 1/day, fresh today, none used
    assert _reroll_quota(0, today, 1) == (0, 1, 1)
    # level 6 → 6/day, 2 used
    assert _reroll_quota(2, today, 6) == (2, 6, 4)
    # used at limit → 0 remaining
    assert _reroll_quota(3, today, 3) == (3, 3, 0)


def test_quota_resets_on_day_change():
    # stale reset_date → effective used resets to 0 regardless of stored count
    eff, limit, left = _reroll_quota(5, '2000-01-01', 3)
    assert eff == 0 and left == 3
