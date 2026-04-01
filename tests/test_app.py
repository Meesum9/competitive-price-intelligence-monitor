"""Tests for the Flask application routes."""

import pytest

import app as flask_app
import database as db


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "app_test.db")
    monkeypatch.setattr("config.DATABASE_PATH", db_path)
    monkeypatch.setattr("database.config.DATABASE_PATH", db_path)
    db.init_db(db_path)

    flask_app.app.config["TESTING"] = True
    flask_app.app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.app.test_client() as client:
        yield client, db_path


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------

def test_index_empty(client):
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"Price Monitor" in resp.data


def test_index_with_product(client):
    c, db_path = client
    db.add_product("Test Widget", "https://example.com", "span.price", db_path=db_path)
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"Test Widget" in resp.data


# ---------------------------------------------------------------------------
# Add product
# ---------------------------------------------------------------------------

def test_add_product_get(client):
    c, _ = client
    resp = c.get("/product/add")
    assert resp.status_code == 200
    assert b"Add Product" in resp.data


def test_add_product_post_valid(client):
    c, db_path = client
    resp = c.post("/product/add", data={
        "name": "My Product",
        "url": "https://shop.example.com/p/1",
        "selector": "p.price",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"My Product" in resp.data
    products = db.get_all_products(db_path=db_path)
    assert len(products) == 1


def test_add_product_post_missing_fields(client):
    c, _ = client
    resp = c.post("/product/add", data={"name": "Incomplete"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"required" in resp.data.lower()


# ---------------------------------------------------------------------------
# Product detail
# ---------------------------------------------------------------------------

def test_product_detail_not_found(client):
    c, _ = client
    resp = c.get("/product/9999")
    assert resp.status_code == 404


def test_product_detail_exists(client):
    c, db_path = client
    pid = db.add_product("Detail Product", "https://detail.com", "p", db_path=db_path)
    db.record_price(pid, 42.99, db_path=db_path)
    resp = c.get(f"/product/{pid}")
    assert resp.status_code == 200
    assert b"Detail Product" in resp.data
    assert b"42.99" in resp.data


# ---------------------------------------------------------------------------
# Edit product
# ---------------------------------------------------------------------------

def test_edit_product_get(client):
    c, db_path = client
    pid = db.add_product("Editable", "https://edit.com", "p", db_path=db_path)
    resp = c.get(f"/product/{pid}/edit")
    assert resp.status_code == 200
    assert b"Editable" in resp.data


def test_edit_product_post(client):
    c, db_path = client
    pid = db.add_product("OldName", "https://old.com", "p", db_path=db_path)
    resp = c.post(f"/product/{pid}/edit", data={
        "name": "NewName",
        "url": "https://new.com",
        "selector": "span.p",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"NewName" in resp.data


# ---------------------------------------------------------------------------
# Delete product
# ---------------------------------------------------------------------------

def test_delete_product(client):
    c, db_path = client
    pid = db.add_product("ToDelete", "https://del.com", "p", db_path=db_path)
    resp = c.post(f"/product/{pid}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert db.get_product(pid, db_path=db_path) is None


# ---------------------------------------------------------------------------
# Alerts view
# ---------------------------------------------------------------------------

def test_alerts_view_empty(client):
    c, _ = client
    resp = c.get("/alerts")
    assert resp.status_code == 200
    assert b"Alerts" in resp.data


def test_alerts_view_shows_alerts(client):
    c, db_path = client
    pid = db.add_product("AlertProd", "https://alert.com", "p", db_path=db_path)
    db.record_alert(pid, 100.0, 80.0, -20.0, db_path=db_path)
    resp = c.get("/alerts")
    assert resp.status_code == 200
    assert b"AlertProd" in resp.data


def test_acknowledge_alert(client):
    c, db_path = client
    pid = db.add_product("AckProd", "https://ack.com", "p", db_path=db_path)
    aid = db.record_alert(pid, 100.0, 90.0, -10.0, db_path=db_path)
    resp = c.post(f"/alerts/{aid}/acknowledge", follow_redirects=True)
    assert resp.status_code == 200
    stored = db.get_alerts(db_path=db_path)
    assert stored[0]["acknowledged"] == 1


def test_acknowledge_all_alerts(client):
    c, db_path = client
    pid = db.add_product("AckAll", "https://ackall.com", "p", db_path=db_path)
    db.record_alert(pid, 100.0, 90.0, -10.0, db_path=db_path)
    db.record_alert(pid, 90.0, 80.0, -11.1, db_path=db_path)
    resp = c.post("/alerts/acknowledge-all", follow_redirects=True)
    assert resp.status_code == 200
    unread = db.get_alerts(unacknowledged_only=True, db_path=db_path)
    assert unread == []
