"""SQLite database layer for the price intelligence monitor.

Schema
------
products
    id          INTEGER  PRIMARY KEY AUTOINCREMENT
    name        TEXT     NOT NULL
    url         TEXT     NOT NULL UNIQUE
    selector    TEXT     NOT NULL   -- CSS selector that targets the price element
    created_at  TEXT     NOT NULL   -- ISO-8601 UTC timestamp

price_history
    id          INTEGER  PRIMARY KEY AUTOINCREMENT
    product_id  INTEGER  NOT NULL   REFERENCES products(id)
    price       REAL     NOT NULL
    scraped_at  TEXT     NOT NULL   -- ISO-8601 UTC timestamp

alerts
    id            INTEGER  PRIMARY KEY AUTOINCREMENT
    product_id    INTEGER  NOT NULL  REFERENCES products(id)
    old_price     REAL     NOT NULL
    new_price     REAL     NOT NULL
    change_pct    REAL     NOT NULL
    triggered_at  TEXT     NOT NULL  -- ISO-8601 UTC timestamp
    acknowledged  INTEGER  NOT NULL DEFAULT 0  -- boolean (0/1)
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _get_conn(db_path: str | None = None):
    conn = sqlite3.connect(db_path or config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db(db_path: str | None = None) -> None:
    """Create tables if they do not already exist."""
    with _get_conn(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                url        TEXT    NOT NULL UNIQUE,
                selector   TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                price      REAL    NOT NULL,
                scraped_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id   INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                old_price    REAL    NOT NULL,
                new_price    REAL    NOT NULL,
                change_pct   REAL    NOT NULL,
                triggered_at TEXT    NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0
            );
            """
        )


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def add_product(name: str, url: str, selector: str,
                db_path: str | None = None) -> int:
    """Insert a new product and return its id."""
    with _get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO products (name, url, selector, created_at) VALUES (?,?,?,?)",
            (name, url, selector, _now_iso()),
        )
        return cur.lastrowid


def get_product(product_id: int, db_path: str | None = None) -> sqlite3.Row | None:
    with _get_conn(db_path) as conn:
        return conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()


def get_all_products(db_path: str | None = None) -> list[sqlite3.Row]:
    with _get_conn(db_path) as conn:
        return conn.execute("SELECT * FROM products ORDER BY name").fetchall()


def delete_product(product_id: int, db_path: str | None = None) -> None:
    with _get_conn(db_path) as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))


def update_product(product_id: int, name: str, url: str, selector: str,
                   db_path: str | None = None) -> None:
    with _get_conn(db_path) as conn:
        conn.execute(
            "UPDATE products SET name=?, url=?, selector=? WHERE id=?",
            (name, url, selector, product_id),
        )


# ---------------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------------

def record_price(product_id: int, price: float,
                 db_path: str | None = None) -> int:
    """Store a scraped price and return its id."""
    with _get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO price_history (product_id, price, scraped_at) VALUES (?,?,?)",
            (product_id, price, _now_iso()),
        )
        return cur.lastrowid


def get_latest_price(product_id: int,
                     db_path: str | None = None) -> float | None:
    """Return the most recently recorded price for a product, or None."""
    with _get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT price FROM price_history WHERE product_id=? ORDER BY scraped_at DESC, id DESC LIMIT 1",
            (product_id,),
        ).fetchone()
        return row["price"] if row else None


def get_price_history(product_id: int, limit: int = 100,
                      db_path: str | None = None) -> list[sqlite3.Row]:
    with _get_conn(db_path) as conn:
        return conn.execute(
            """SELECT price, scraped_at FROM price_history
               WHERE product_id=? ORDER BY scraped_at DESC LIMIT ?""",
            (product_id, limit),
        ).fetchall()


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def record_alert(product_id: int, old_price: float, new_price: float,
                 change_pct: float, db_path: str | None = None) -> int:
    with _get_conn(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO alerts
               (product_id, old_price, new_price, change_pct, triggered_at, acknowledged)
               VALUES (?,?,?,?,?,0)""",
            (product_id, old_price, new_price, change_pct, _now_iso()),
        )
        return cur.lastrowid


def get_alerts(product_id: int | None = None, unacknowledged_only: bool = False,
               limit: int = 200, db_path: str | None = None) -> list[sqlite3.Row]:
    filters: list[str] = []
    params: list = []
    if product_id is not None:
        filters.append("a.product_id = ?")
        params.append(product_id)
    if unacknowledged_only:
        filters.append("a.acknowledged = 0")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params.append(limit)
    with _get_conn(db_path) as conn:
        return conn.execute(
            f"""SELECT a.*, p.name AS product_name
                FROM alerts a JOIN products p ON a.product_id = p.id
                {where}
                ORDER BY a.triggered_at DESC LIMIT ?""",
            params,
        ).fetchall()


def acknowledge_alert(alert_id: int, db_path: str | None = None) -> None:
    with _get_conn(db_path) as conn:
        conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))


def acknowledge_all_alerts(db_path: str | None = None) -> None:
    with _get_conn(db_path) as conn:
        conn.execute("UPDATE alerts SET acknowledged=1")
