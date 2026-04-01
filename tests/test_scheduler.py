"""Tests for the scheduler / scrape-cycle orchestration."""

import pytest
from unittest.mock import patch, MagicMock

import database as db
import scheduler


@pytest.fixture
def tmp_db(tmp_path):
    path = str(tmp_path / "sched_test.db")
    db.init_db(path)
    return path


@pytest.fixture
def product_id(tmp_db):
    return db.add_product("Sched Product", "https://sched.example.com", "p.price", db_path=tmp_db)


def test_run_scrape_cycle_no_products(tmp_db):
    summary = scheduler.run_scrape_cycle(db_path=tmp_db)
    assert summary == {"scraped": 0, "failed": 0, "alerted": 0}


def test_run_scrape_cycle_success(tmp_db, product_id):
    with patch("scheduler.scraper.scrape_all") as mock_scrape:
        mock_scrape.return_value = {product_id: 49.99}
        summary = scheduler.run_scrape_cycle(db_path=tmp_db)

    assert summary["scraped"] == 1
    assert summary["failed"] == 0
    assert db.get_latest_price(product_id, db_path=tmp_db) == pytest.approx(49.99)


def test_run_scrape_cycle_with_alert(tmp_db, product_id):
    # Prime with an initial price
    db.record_price(product_id, 100.0, db_path=tmp_db)

    with patch("scheduler.scraper.scrape_all") as mock_scrape:
        mock_scrape.return_value = {product_id: 50.0}  # 50% drop → alert
        summary = scheduler.run_scrape_cycle(db_path=tmp_db)

    assert summary["alerted"] == 1
    stored_alerts = db.get_alerts(db_path=tmp_db)
    assert len(stored_alerts) == 1


def test_run_scrape_cycle_failed_product(tmp_db, product_id):
    with patch("scheduler.scraper.scrape_all") as mock_scrape:
        mock_scrape.return_value = {product_id: ValueError("bad selector")}
        summary = scheduler.run_scrape_cycle(db_path=tmp_db)

    assert summary["scraped"] == 0
    assert summary["failed"] == 1
    assert db.get_latest_price(product_id, db_path=tmp_db) is None
