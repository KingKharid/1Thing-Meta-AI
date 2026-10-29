"""Thin WhatsApp Cloud API sender.

Delivery must never break ingestion: if credentials are absent (local
dev, pytest, the offline demo) the sender logs and returns ``False``
instead of raising. Configure with:

    WHATSAPP_ACCESS_TOKEN
    WHATSAPP_PHONE_NUMBER_ID
    WHATSAPP_GRAPH_VERSION   (optional, defaults to v21.0)
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger("onething.whatsapp")

_TIMEOUT_SECONDS = 10

# Interactive message body budget (Cloud API hard limit is 1024).
_MAX_INTERACTIVE_BODY = 1024


def _credentials() -> tuple[str, str, str]:
    token = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
    phone_id = (os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    version = (os.getenv("WHATSAPP_GRAPH_VERSION") or "v21.0").strip()
    return token, phone_id, version


def is_configured() -> bool:
    token, phone_id, _ = _credentials()
    return bool(token and phone_id)


def _post(payload: dict) -> bool:
    token, phone_id, version = _credentials()
    if not (token and phone_id):
        logger.info("WhatsApp send skipped: credentials not configured")
        return False

    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    try:
        res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("WhatsApp send failed: %s", exc)
        return False

    if res.status_code >= 400:
        logger.warning(
            "WhatsApp send rejected (%s): %s", res.status_code, res.text[:300]
        )
        return False
    return True


def _recipient(to: str) -> str:
    return (to or "").strip()


def send_text(to: str, body: str) -> bool:
    """Send a plain-text WhatsApp message. Returns True when accepted."""
    recipient = _recipient(to)
    if not recipient or recipient == "unknown" or not body:
        return False

    return _post(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
    )


def send_focus_message(to: str, body: str, task_id: int) -> bool:
    """Send the focus reply with native DONE / SKIP quick-reply buttons.

    Falls back to a plain text message when the body exceeds the
    interactive budget, when no task id is available, or when Meta
    rejects the interactive payload — the user always gets the reply.
    """
    recipient = _recipient(to)
    if not recipient or recipient == "unknown" or not body:
        return False

    if task_id is None or task_id < 0 or len(body) > _MAX_INTERACTIVE_BODY:
        return send_text(recipient, body)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": f"done:{task_id}", "title": "DONE"},
                    },
                    {
                        "type": "reply",
                        "reply": {"id": f"skip:{task_id}", "title": "SKIP"},
                    },
                ]
            },
        },
    }
    if _post(payload):
        return True
    # Interactive can be rejected (e.g. template/session rules); text cannot.
    return send_text(recipient, body)


__all__ = ["is_configured", "send_focus_message", "send_text"]
