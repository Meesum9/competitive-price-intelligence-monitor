from __future__ import annotations

RAW_PRICES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL,
  site TEXT NOT NULL,
  url TEXT NOT NULL,
  name TEXT,
  title TEXT,
  price REAL,
  currency TEXT,
  price_text TEXT,
  scraped_at TEXT NOT NULL
);
"""

PRICE_HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL,
  price REAL,
  currency TEXT,
  scraped_at TEXT NOT NULL
);
"""

LATEST_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_price_history_product_time
ON price_history (product_id, scraped_at);
"""

RAW_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_raw_prices_product_time
ON raw_prices (product_id, scraped_at);
"""
