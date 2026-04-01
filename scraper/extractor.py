from __future__ import annotations

import datetime
import re
from typing import Any, Dict, Optional, Tuple

import requests

import config
from intelligence.alerter import send_webhook
from intelligence.diff_engine import compute_diff, should_alert
from scraper.parser import parse_product
from storage.db import (
    fetch_last_two_prices,
    init_db,
    insert_price_history,
    insert_raw_price,
)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_page(url: str, timeout_seconds: int = 15) -> str:
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout_seconds)
    resp.raise_for_status()
    return resp.text


def normalize_price(price_text: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    if not price_text:
        return None, None

    currency = None
    if "£" in price_text:
        currency = "GBP"
    elif "$" in price_text:
        currency = "USD"
    elif "€" in price_text:
        currency = "EUR"

    cleaned = price_text.strip()
    cleaned = cleaned.replace(",", "")
    cleaned = re.sub(r"[^0-9.]+", "", cleaned)
    if not cleaned:
        return None, currency

    try:
        return float(cleaned), currency
    except ValueError:
        return None, currency


def scrape_target(target: Dict[str, Any]) -> Dict[str, Any]:
    html = fetch_page(target["url"])
    parsed = parse_product(target["site"], html)
    price, inferred_currency = normalize_price(parsed.price_text)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "product_id": target["product_id"],
        "site": target["site"],
        "url": target["url"],
        "name": target.get("name"),
        "title": parsed.title,
        "price": price,
        "currency": target.get("currency") or inferred_currency or config.DEFAULT_CURRENCY,
        "price_text": parsed.price_text,
        "scraped_at": scraped_at,
    }


def maybe_alert(row: Dict[str, Any]) -> None:
    history = fetch_last_two_prices(config.DB_PATH, row["product_id"])
    if len(history) < 2:
        return

    new = history[0]
    old = history[1]

    diff = compute_diff(row["product_id"], old.get("price"), new.get("price"))

    alert_cfg = None
    for t in config.TARGETS:
        if t.get("product_id") == row["product_id"]:
            alert_cfg = t.get("alert") or {}
            break

    pct_drop = float((alert_cfg or {}).get("pct_drop", 0.0))
    pct_rise = float((alert_cfg or {}).get("pct_rise", 0.0))

    if not should_alert(diff.pct_change, pct_drop=pct_drop, pct_rise=pct_rise):
        return

    send_webhook(
        config.ALERT_WEBHOOK_URL,
        {
            "event": "price_change",
            "product_id": row["product_id"],
            "site": row["site"],
            "url": row["url"],
            "old_price": diff.old_price,
            "new_price": diff.new_price,
            "pct_change": diff.pct_change,
            "scraped_at": row["scraped_at"],
        },
    )


def run_scrape_once() -> None:
    init_db(config.DB_PATH)

    for target in config.TARGETS:
        row = scrape_target(target)
        insert_raw_price(config.DB_PATH, row)
        insert_price_history(
            config.DB_PATH,
            product_id=row["product_id"],
            price=row.get("price"),
            currency=row.get("currency"),
            scraped_at=row["scraped_at"],
        )
        maybe_alert(row)


if __name__ == "__main__":
    run_scrape_once()