import pytest

from core.config import Settings


def test_summary_days_must_be_positive(monkeypatch):
    for bad in ("0", "-3", "삼십"):
        monkeypatch.setenv("SUMMARY_DAYS", bad)
        with pytest.raises(ValueError, match="SUMMARY_DAYS"):
            Settings.load()
    monkeypatch.setenv("SUMMARY_DAYS", "30")
    assert Settings.load().summary_days == 30
