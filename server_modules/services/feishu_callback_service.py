import os

from server_modules.services.daily_feishu_runtime import product_template_callback_card


def _callback_action_value(payload):
    event = payload.get("event") if isinstance(payload, dict) else {}
    event = event if isinstance(event, dict) else {}
    action = event.get("action") or payload.get("action") or {}
    if not isinstance(action, dict):
        return {}
    value = action.get("value") or {}
    return value if isinstance(value, dict) else {}


def _valid_callback_token(payload):
    expected = os.environ.get("FEISHU_CALLBACK_TOKEN", "").strip()
    if not expected:
        return True
    actual = str((payload or {}).get("token") or ((payload or {}).get("event") or {}).get("token") or "").strip()
    return actual == expected


def handle_card_action(payload):
    payload = payload if isinstance(payload, dict) else {}
    if payload.get("challenge"):
        return {"challenge": payload.get("challenge")}
    if not _valid_callback_token(payload):
        return {"toast": {"type": "error", "content": "Unauthorized callback."}}

    value = _callback_action_value(payload)
    if value.get("action") != "switch_daily_report_view":
        return {"toast": {"type": "info", "content": "Unsupported action."}}

    view_slot = value.get("view_slot") or value.get("view") or "product_1"
    if not str(view_slot).startswith("product_"):
        return {"toast": {"type": "info", "content": "Only product views are supported."}}

    return {
        "card": product_template_callback_card(view_slot=view_slot),
    }
