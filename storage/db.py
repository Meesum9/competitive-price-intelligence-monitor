from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from storage.models import (
    LATEST_INDEX_SQL,
    PRICE_HISTORY_TABLE_SQL,
    RAW_INDEX_SQL,
    RAW_PRICES_TABLE_SQL,
)


def ensure_parent_dir(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str) -> sqlite3.Connection:
    ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(RAW_PRICES_TABLE_SQL)
        conn.execute(PRICE_HISTORY_TABLE_SQL)
        conn.execute(RAW_INDEX_SQL)
        conn.execute(LATEST_INDEX_SQL)
        conn.commit()


def insert_raw_price(db_path: str, row: Dict[str, Any]) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO raw_prices (
              product_id, site, url, name, title, price, currency, price_text, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("product_id"),
                row.get("site"),
                row.get("url"),
                row.get("name"),
                row.get("title"),
                row.get("price"),
                row.get("currency"),
                row.get("price_text"),
                row.get("scraped_at"),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def insert_price_history(db_path: str, product_id: str, price: Optional[float], currency: Optional[str], scraped_at: str) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO price_history (product_id, price, currency, scraped_at)
            VALUES (?, ?, ?, ?)
            """,
            (product_id, price, currency, scraped_at),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_latest_prices(db_path: str) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT r.*
            FROM raw_prices r
            JOIN (
              SELECT product_id, MAX(scraped_at) AS max_ts
              FROM raw_prices
              GROUP BY product_id
            ) latest
            ON r.product_id = latest.product_id AND r.scraped_at = latest.max_ts
            ORDER BY r.product_id
            """
        ).fetchall()
        return [dict(x) for x in rows]


def fetch_price_history(db_path: str, product_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT product_id, price, currency, scraped_at
            FROM price_history
            WHERE product_id = ?
            ORDER BY scraped_at DESC
            LIMIT ?
            """,
            (product_id, limit),
        ).fetchall()
        return [dict(x) for x in rows]


def fetch_last_two_prices(db_path: str, product_id: str) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT product_id, price, currency, scraped_at
            FROM price_history
            WHERE product_id = ?
            ORDER BY scraped_at DESC
            LIMIT 2
            """,
            (product_id,),
        ).fetchall()
        return [dict(x) for x in rows]
