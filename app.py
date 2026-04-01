"""Flask dashboard for the competitive price intelligence monitor."""

import logging

from flask import Flask, abort, flash, redirect, render_template, request, url_for

import config
import database as db
import scheduler as sched

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s – %(message)s",
)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ---------------------------------------------------------------------------
# Initialise DB on first request
# ---------------------------------------------------------------------------

with app.app_context():
    db.init_db()


# ---------------------------------------------------------------------------
# Dashboard – product list
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    products = db.get_all_products()
    # Annotate each product with its latest price
    enriched = []
    for p in products:
        latest = db.get_latest_price(p["id"])
        history = db.get_price_history(p["id"], limit=2)
        prev_price = history[1]["price"] if len(history) >= 2 else None
        enriched.append({
            "id": p["id"],
            "name": p["name"],
            "url": p["url"],
            "selector": p["selector"],
            "latest_price": latest,
            "prev_price": prev_price,
        })

    unacknowledged = len(db.get_alerts(unacknowledged_only=True))
    return render_template("index.html", products=enriched, unacknowledged=unacknowledged)


# ---------------------------------------------------------------------------
# Product detail
# ---------------------------------------------------------------------------

@app.route("/product/<int:product_id>")
def product_detail(product_id: int):
    product = db.get_product(product_id)
    if product is None:
        abort(404)
    history = db.get_price_history(product_id, limit=100)
    product_alerts = db.get_alerts(product_id=product_id, limit=50)
    return render_template(
        "product.html",
        product=product,
        history=history,
        alerts=product_alerts,
    )


# ---------------------------------------------------------------------------
# Add product
# ---------------------------------------------------------------------------

@app.route("/product/add", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        url = request.form.get("url", "").strip()
        selector = request.form.get("selector", "").strip()
        if not (name and url and selector):
            flash("All fields are required.", "error")
            return render_template("add_product.html")
        try:
            db.add_product(name, url, selector)
            flash(f"Product '{name}' added successfully.", "success")
            return redirect(url_for("index"))
        except Exception as exc:
            flash(f"Could not add product: {exc}", "error")
    return render_template("add_product.html")


# ---------------------------------------------------------------------------
# Edit product
# ---------------------------------------------------------------------------

@app.route("/product/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id: int):
    product = db.get_product(product_id)
    if product is None:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        url = request.form.get("url", "").strip()
        selector = request.form.get("selector", "").strip()
        if not (name and url and selector):
            flash("All fields are required.", "error")
            return render_template("edit_product.html", product=product)
        db.update_product(product_id, name, url, selector)
        flash(f"Product '{name}' updated.", "success")
        return redirect(url_for("product_detail", product_id=product_id))
    return render_template("edit_product.html", product=product)


# ---------------------------------------------------------------------------
# Delete product
# ---------------------------------------------------------------------------

@app.route("/product/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id: int):
    product = db.get_product(product_id)
    if product is None:
        abort(404)
    name = product["name"]
    db.delete_product(product_id)
    flash(f"Product '{name}' deleted.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@app.route("/alerts")
def alerts_view():
    all_alerts = db.get_alerts(limit=200)
    return render_template("alerts.html", alerts=all_alerts)


@app.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id: int):
    db.acknowledge_alert(alert_id)
    flash("Alert acknowledged.", "success")
    return redirect(url_for("alerts_view"))


@app.route("/alerts/acknowledge-all", methods=["POST"])
def acknowledge_all():
    db.acknowledge_all_alerts()
    flash("All alerts acknowledged.", "success")
    return redirect(url_for("alerts_view"))


# ---------------------------------------------------------------------------
# Manual scrape trigger
# ---------------------------------------------------------------------------

@app.route("/scrape", methods=["POST"])
def trigger_scrape():
    summary = sched.run_scrape_cycle()
    flash(
        f"Scrape complete – scraped {summary['scraped']}, "
        f"failed {summary['failed']}, alerted {summary['alerted']}.",
        "info",
    )
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
