"""
Unit tests for is_open_now().

Google Places periods: day 0=Sun, 1=Mon … 6=Sat; time "HHMM".
Python weekday(): 0=Mon … 6=Sun → conversion: google_day = (weekday + 1) % 7.
"""
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.bounty import is_open_now

TZ = ZoneInfo('Asia/Taipei')

# Helpers to build fake "now" without hitting real clock
def _dt(weekday_python: int, hour: int, minute: int = 0) -> datetime:
    """Build a fixed datetime with the given Python weekday (0=Mon…6=Sun)."""
    # Use a known Monday as anchor: 2026-06-15 is Monday
    from datetime import timedelta
    anchor = datetime(2026, 6, 15, tzinfo=TZ)  # Monday
    return anchor + timedelta(days=weekday_python, hours=hour, minutes=minute)


def _hours(*periods) -> dict:
    """Convenience: wrap period dicts in the opening_hours JSONB shape."""
    return {'periods': list(periods)}


def _period(open_day, open_time, close_day, close_time):
    return {
        'open':  {'day': open_day,  'time': open_time},
        'close': {'day': close_day, 'time': close_time},
    }


# ── 1. 一般同日時段 ──────────────────────────────────────────────────────────
class TestSameDay:
    OH = _hours(_period(1, '1100', 1, '2100'))  # Mon 11:00-21:00

    def test_open_at_noon(self):
        assert is_open_now(self.OH, _dt(0, 12)) is True  # Mon noon

    def test_open_at_exact_open(self):
        assert is_open_now(self.OH, _dt(0, 11, 0)) is True

    def test_open_at_exact_close(self):
        assert is_open_now(self.OH, _dt(0, 21, 0)) is True

    def test_closed_before_open(self):
        assert is_open_now(self.OH, _dt(0, 10, 59)) is False

    def test_closed_after_close(self):
        assert is_open_now(self.OH, _dt(0, 21, 1)) is False

    def test_wrong_day(self):
        # Tuesday — not covered by Mon-only period
        assert is_open_now(self.OH, _dt(1, 12)) is False


# ── 2. 跨夜時段 ──────────────────────────────────────────────────────────────
class TestOvernight:
    # Sat 18:00 → Sun 02:00 (Google: Sat=6, Sun=0)
    OH = _hours(_period(6, '1800', 0, '0200'))

    def test_open_saturday_evening(self):
        # Python Sat = weekday 5; google_day = (5+1)%7 = 6 ✓
        assert is_open_now(self.OH, _dt(5, 20)) is True

    def test_open_at_midnight_saturday(self):
        assert is_open_now(self.OH, _dt(5, 23, 59)) is True

    def test_open_sunday_before_close(self):
        # After midnight, still open until 02:00 on Sunday
        # Python Sun = weekday 6; google_day = (6+1)%7 = 0 ✓
        assert is_open_now(self.OH, _dt(6, 1, 30)) is True

    def test_closed_sunday_after_close(self):
        assert is_open_now(self.OH, _dt(6, 2, 1)) is False

    def test_closed_saturday_before_open(self):
        assert is_open_now(self.OH, _dt(5, 17, 59)) is False


# ── 3. 同日多段（午間 + 晚間）────────────────────────────────────────────────
class TestMultiPeriod:
    # Wed: lunch 11:30-14:00, dinner 17:30-21:30 (Google: Wed=3)
    OH = _hours(
        _period(3, '1130', 3, '1400'),
        _period(3, '1730', 3, '2130'),
    )

    def test_open_lunch(self):
        # Python Wed = weekday 2; google_day = (2+1)%7 = 3 ✓
        assert is_open_now(self.OH, _dt(2, 12)) is True

    def test_closed_between_periods(self):
        assert is_open_now(self.OH, _dt(2, 15)) is False

    def test_open_dinner(self):
        assert is_open_now(self.OH, _dt(2, 19)) is True

    def test_closed_after_dinner(self):
        assert is_open_now(self.OH, _dt(2, 22)) is False

    def test_closed_wrong_day(self):
        assert is_open_now(self.OH, _dt(0, 12)) is False  # Monday


# ── 4. 無資料 / 缺欄位 ────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_none_returns_none(self):
        assert is_open_now(None) is None

    def test_empty_dict_returns_none(self):
        assert is_open_now({}) is None

    def test_empty_periods_returns_none(self):
        assert is_open_now({'periods': []}) is None
