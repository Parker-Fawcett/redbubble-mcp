import datetime as dt

import pytest

from redbubble_mcp.guards import RB_MAX_UPLOADS_PER_DAY, UploadBlocked, UploadLedger

NOW = dt.datetime(2026, 10, 21, 12, 0, 0)
LATER = NOW + dt.timedelta(minutes=6)
SOON = NOW + dt.timedelta(minutes=1)


@pytest.fixture()
def ledger(tmp_path):
    return UploadLedger(state_dir=str(tmp_path))


def test_is_clear_before_any_uploads(ledger):
    ledger.assert_can_upload(NOW)


def test_blocks_at_daily_cap(ledger):
    for i in range(RB_MAX_UPLOADS_PER_DAY):
        ledger.record_upload(NOW + dt.timedelta(minutes=i), force=True)
    with pytest.raises(UploadBlocked) as exc:
        ledger.assert_can_upload(LATER)
    assert "30" in str(exc.value)


def test_resets_on_new_day(ledger):
    for i in range(RB_MAX_UPLOADS_PER_DAY):
        ledger.record_upload(NOW + dt.timedelta(minutes=i), force=True)
    next_day = NOW + dt.timedelta(days=1)
    ledger.assert_can_upload(next_day)  # must not raise


def test_respects_min_interval(ledger):
    ledger.record_upload(NOW)
    with pytest.raises(UploadBlocked) as exc:
        ledger.assert_can_upload(SOON)
    assert exc.value.retry_after_s > 0


def test_allows_upload_after_interval(ledger):
    ledger.record_upload(NOW)
    ledger.assert_can_upload(LATER)


def test_record_persists(tmp_path):
    ledger = UploadLedger(state_dir=str(tmp_path))
    ledger.record_upload(NOW, force=True)
    reopened = UploadLedger(state_dir=str(tmp_path))
    assert reopened.count_on(NOW.date()) == 1


def test_bypass_guard_when_explicitly_disabled(ledger):
    ledger.record_upload(NOW, force=True)
    # bypass=True lets the assistant override cap/interval checks explicitly
    ledger.assert_can_upload(SOON, bypass=True)


def test_default_interval_is_conservative(ledger):
    ledger.record_upload(NOW)
    with pytest.raises(UploadBlocked):
        ledger.assert_can_upload(NOW + dt.timedelta(seconds=30))
