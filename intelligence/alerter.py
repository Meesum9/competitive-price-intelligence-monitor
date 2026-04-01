from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests


def send_webhook(webhook_url: Optional[str], payload: Dict[str, Any]) -> None:
    if not webhook_url:
        return

    requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
