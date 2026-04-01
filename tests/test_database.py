"""Tests for the database module."""

import os
import sqlite3
import tempfile

import pytest

import database as db


@pytest.fixture
def tmp_db(tmp_path):
    path = str(tmp_path / "test.db")
    db.init_db(path)
    return path


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def test_init_db_creates_tables(tmp_db):
    conn = sqlite3.connect(tmp_db)
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert {"products", "price_history", "alerts"}.issubset(tables)


def test_init_db_idempotent(tmp_db):
    """Calling init_db twice must not raise."""
    db.init_db(tmp_db)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def test_add_and_get_product(tmp_db):
    pid = db.add_product("Widget A", "https://example.com/a", "span.price", db_path=tmp_db)
    assert isinstance(pid, int)
    product = db.get_product(pid, db_path=tmp_db)
    assert product is not None
    assert product["name"] == "Widget A"
    assert product["url"] == "https://example.com/a"
    assert product["selector"] == "span.price"


def test_get_product_not_found(tmp_db):
    assert db.get_product(9999, db_path=tmp_db) is None


def test_get_all_products_empty(tmp_db):
    assert db.get_all_products(db_path=tmp_db) == []


def test_get_all_products_ordered_by_name(tmp_db):
    db.add_product("Zebra", "https://example.com/z", "p", db_path=tmp_db)
    db.add_product("Apple", "https://example.com/a", "p", db_path=tmp_db)
    names = [p["name"] for p in db.get_all_products(db_path=tmp_db)]
    assert names == sorted(names)


def test_update_product(tmp_db):
    pid = db.add_product("Old Name", "https://old.com", "div.price", db_path=tmp_db)
    db.update_product(pid, "New Name", "https://new.com", "span.p", db_path=tmp_db)
    p = db.get_product(pid, db_path=tmp_db)
    assert p["name"] == "New Name"
    assert p["url"] == "https://new.com"
    assert p["selector"] == "span.p"


def test_delete_product(tmp_db):
    pid = db.add_product("Temp", "https://tmp.com", "p", db_path=tmp_db)
    db.delete_product(pid, db_path=tmp_db)
    assert db.get_product(pid, db_path=tmp_db) is None


def test_delete_product_cascades_price_history(tmp_db):
    pid = db.add_product("Cascade", "https://cascade.com", "p", db_path=tmp_db)
    db.record_price(pid, 9.99, db_path=tmp_db)
    db.delete_product(pid, db_path=tmp_db)
    # Price history should be gone
    assert db.get_price_history(pid, db_path=tmp_db) == []


# ---------------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------------

def test_record_and_get_latest_price(tmp_db):
    pid = db.add_product("P", "https://p.com", "p", db_path=tmp_db)
    db.record_price(pid, 10.00, db_path=tmp_db)
    db.record_price(pid, 12.50, db_path=tmp_db)
    assert db.get_latest_price(pid, db_path=tmp_db) == pytest.approx(12.50)


def test_get_latest_price_no_history(tmp_db):
    pid = db.add_product("P2", "https://p2.com", "p", db_path=tmp_db)
    assert db.get_latest_price(pid, db_path=tmp_db) is None


def test_get_price_history_limit(tmp_db):
    pid = db.add_product("P3", "https://p3.com", "p", db_path=tmp_db)
    for i in range(5):
        db.record_price(pid, float(i), db_path=tmp_db)
    history = db.get_price_history(pid, limit=3, db_path=tmp_db)
    assert len(history) == 3


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def test_record_and_get_alert(tmp_db):
    pid = db.add_product("PA", "https://pa.com", "p", db_path=tmp_db)
    aid = db.record_alert(pid, 10.0, 8.0, -20.0, db_path=tmp_db)
    alerts = db.get_alerts(db_path=tmp_db)
    assert len(alerts) == 1
    assert alerts[0]["id"] == aid
    assert alerts[0]["change_pct"] == pytest.approx(-20.0)
    assert alerts[0]["acknowledged"] == 0


def test_acknowledge_alert(tmp_db):
    pid = db.add_product("PB", "https://pb.com", "p", db_path=tmp_db)
    aid = db.record_alert(pid, 10.0, 9.0, -10.0, db_path=tmp_db)
    db.acknowledge_alert(aid, db_path=tmp_db)
    alerts = db.get_alerts(db_path=tmp_db)
    assert alerts[0]["acknowledged"] == 1


def test_acknowledge_all_alerts(tmp_db):
    pid = db.add_product("PC", "https://pc.com", "p", db_path=tmp_db)
    for price in [9.0, 8.0, 7.0]:
        db.record_alert(pid, 10.0, price, -10.0, db_path=tmp_db)
    db.acknowledge_all_alerts(db_path=tmp_db)
    unread = db.get_alerts(unacknowledged_only=True, db_path=tmp_db)
    assert unread == []


def test_get_alerts_unacknowledged_only(tmp_db):
    pid = db.add_product("PD", "https://pd.com", "p", db_path=tmp_db)
    aid1 = db.record_alert(pid, 10.0, 9.0, -10.0, db_path=tmp_db)
    aid2 = db.record_alert(pid, 9.0, 8.0, -11.1, db_path=tmp_db)
    db.acknowledge_alert(aid1, db_path=tmp_db)
    unread = db.get_alerts(unacknowledged_only=True, db_path=tmp_db)
    assert len(unread) == 1
    assert unread[0]["id"] == aid2


def test_get_alerts_by_product(tmp_db):
    pid1 = db.add_product("PE1", "https://pe1.com", "p", db_path=tmp_db)
    pid2 = db.add_product("PE2", "https://pe2.com", "p", db_path=tmp_db)
    db.record_alert(pid1, 10.0, 9.0, -10.0, db_path=tmp_db)
    db.record_alert(pid2, 20.0, 18.0, -10.0, db_path=tmp_db)
    alerts_for_1 = db.get_alerts(product_id=pid1, db_path=tmp_db)
    assert len(alerts_for_1) == 1
    assert alerts_for_1[0]["product_id"] == pid1
