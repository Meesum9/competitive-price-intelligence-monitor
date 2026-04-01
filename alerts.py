"""Price-change alert engine.

Compares a newly scraped price against the last recorded price and, when
the change exceeds the configured thresholds, stores an alert in the
database and optionally delivers it via email.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional

import config
import database as db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core detection logic
# ---------------------------------------------------------------------------

def check_and_alert(product_id: int, new_price: float,
                    db_path: str | None = None) -> Optional[dict]:
    """Compare *new_price* with the last stored price for *product_id*.

    If the change exceeds the configured thresholds:
      1. Persists an alert row in the database.
      2. Attempts to send an email notification (if SMTP is configured).

    Returns a dict describing the alert when one is triggered, else ``None``.
    """
    old_price = db.get_latest_price(product_id, db_path=db_path)

    if old_price is None:
        # First observation for this product – no alert yet
        return None

    absolute_change = abs(new_price - old_price)
    if old_price == 0:
        change_pct = 0.0
    else:
        change_pct = (new_price - old_price) / old_price * 100.0

    if (absolute_change < config.ALERT_MIN_CHANGE
            or abs(change_pct) < config.ALERT_THRESHOLD_PCT):
        return None

    # Thresholds exceeded – record and deliver alert
    alert_id = db.record_alert(
        product_id=product_id,
        old_price=old_price,
        new_price=new_price,
        change_pct=change_pct,
        db_path=db_path,
    )

    product = db.get_product(product_id, db_path=db_path)
    product_name = product["name"] if product else f"product #{product_id}"

    direction = "dropped" if new_price < old_price else "increased"
    alert_info = {
        "id": alert_id,
        "product_id": product_id,
        "product_name": product_name,
        "old_price": old_price,
        "new_price": new_price,
        "change_pct": change_pct,
        "direction": direction,
    }

    logger.info(
        "ALERT [%s] %s %.2f → %.2f (%.2f%%)",
        product_name, direction, old_price, new_price, change_pct,
    )

    _send_email_alert(alert_info)
    return alert_info


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------

def _send_email_alert(alert: dict) -> None:
    """Send an email alert if SMTP credentials are configured."""
    if not (config.SMTP_HOST and config.SMTP_USER and config.ALERT_TO):
        return  # Email not configured

    recipients = [r.strip() for r in config.ALERT_TO.split(",") if r.strip()]
    if not recipients:
        return

    direction = alert["direction"]
    subject = (
        f"Price Alert: {alert['product_name']} has {direction} "
        f"by {abs(alert['change_pct']):.1f}%"
    )
    body = (
        f"Product   : {alert['product_name']}\n"
        f"Direction : {direction.capitalize()}\n"
        f"Old price : {alert['old_price']:.2f}\n"
        f"New price : {alert['new_price']:.2f}\n"
        f"Change    : {alert['change_pct']:+.2f}%\n"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.ALERT_FROM or config.SMTP_USER
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
            smtp.sendmail(msg["From"], recipients, msg.as_string())
        logger.info("Email alert sent to %s", recipients)
    except Exception as exc:
        logger.error("Failed to send email alert: %s", exc)
