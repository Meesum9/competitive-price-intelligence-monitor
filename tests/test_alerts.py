"""Tests for the alerts module."""

import pytest

import alerts
import database as db


@pytest.fixture
def tmp_db(tmp_path):
    path = str(tmp_path / "alerts_test.db")
    db.init_db(path)
    return path


@pytest.fixture
def product_id(tmp_db):
    return db.add_product("Test Product", "https://example.com", "p.price", db_path=tmp_db)


# ---------------------------------------------------------------------------
# No previous price – should never alert
# ---------------------------------------------------------------------------

def test_no_alert_on_first_observation(tmp_db, product_id):
    result = alerts.check_and_alert(product_id, 100.0, db_path=tmp_db)
    assert result is None


# ---------------------------------------------------------------------------
# Below threshold – no alert
# ---------------------------------------------------------------------------

def test_no_alert_below_threshold(tmp_db, product_id):
    db.record_price(product_id, 100.0, db_path=tmp_db)
    # 0.5% change – below default 1% threshold
    result = alerts.check_and_alert(product_id, 100.5, db_path=tmp_db)
    assert result is None


def test_no_alert_zero_absolute_change(tmp_db, product_id):
    db.record_price(product_id, 50.0, db_path=tmp_db)
    result = alerts.check_and_alert(product_id, 50.0, db_path=tmp_db)
    assert result is None


# ---------------------------------------------------------------------------
# Above threshold – alert triggered
# ---------------------------------------------------------------------------

def test_alert_on_price_drop(tmp_db, product_id):
    db.record_price(product_id, 100.0, db_path=tmp_db)
    result = alerts.check_and_alert(product_id, 80.0, db_path=tmp_db)
    assert result is not None
    assert result["direction"] == "dropped"
    assert result["old_price"] == pytest.approx(100.0)
    assert result["new_price"] == pytest.approx(80.0)
    assert result["change_pct"] == pytest.approx(-20.0)


def test_alert_on_price_increase(tmp_db, product_id):
    db.record_price(product_id, 100.0, db_path=tmp_db)
    result = alerts.check_and_alert(product_id, 120.0, db_path=tmp_db)
    assert result is not None
    assert result["direction"] == "increased"
    assert result["change_pct"] == pytest.approx(20.0)


def test_alert_persisted_in_db(tmp_db, product_id):
    db.record_price(product_id, 100.0, db_path=tmp_db)
    alerts.check_and_alert(product_id, 80.0, db_path=tmp_db)
    stored = db.get_alerts(product_id=product_id, db_path=tmp_db)
    assert len(stored) == 1
    assert stored[0]["new_price"] == pytest.approx(80.0)


def test_no_email_without_smtp_config(tmp_db, product_id, monkeypatch):
    """Email sending should be skipped when SMTP is not configured."""
    monkeypatch.setattr("config.SMTP_HOST", "")
    db.record_price(product_id, 100.0, db_path=tmp_db)
    # Should not raise even though SMTP is unconfigured
    result = alerts.check_and_alert(product_id, 50.0, db_path=tmp_db)
    assert result is not None
