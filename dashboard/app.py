from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from storage.db import fetch_latest_prices, fetch_price_history, init_db

app = Flask(__name__)


@app.get("/")
def index():
    init_db(config.DB_PATH)
    latest = fetch_latest_prices(config.DB_PATH)

    selected_product_id = request.args.get("product_id")
    history = None
    if selected_product_id:
        history = list(reversed(fetch_price_history(config.DB_PATH, selected_product_id, limit=200)))

    return render_template(
        "index.html",
        latest=latest,
        selected_product_id=selected_product_id,
        history=history,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
