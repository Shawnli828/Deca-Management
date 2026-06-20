import os

from server_modules.services.feishu_card_snapshot_service import load_daily_report_snapshot
from server_modules.services.daily_feishu_runtime import product_template_callback_card


def _first_text_value(data, keys):
    if not isinstance(data, dict):
        return ""
    for key in keys:
        value = data.get(key)
        if value is not None:
            return str(value or "").strip()
    return ""


def _callback_action_value(payload):
    event = payload.get("event") if isinstance(payload, dict) else {}
    event = event if isinstance(event, dict) else {}
    action = event.get("action") or payload.get("action") or {}
    if not isinstance(action, dict):
        return {}
    value = action.get("value") or {}
    return value if isinstance(value, dict) else {}


def _callback_message_id(payload):
    payload = payload if isinstance(payload, dict) else {}
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    context = event.get("context") if isinstance(event.get("context"), dict) else {}
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    return (
        _first_text_value(context, ("open_message_id", "message_id"))
        or _first_text_value(event, ("open_message_id", "message_id"))
        or _first_text_value(message, ("open_message_id", "message_id"))
        or _first_text_value(payload, ("open_message_id", "message_id"))
    )


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
    report_date = value.get("report_date") or value.get("biz_date") or ""
    if not str(view_slot).startswith("product_"):
        return {"toast": {"type": "info", "content": "Only product views are supported."}}

    snapshot = load_daily_report_snapshot(_callback_message_id(payload))
    if snapshot:
        return {
            "card": product_template_callback_card(
                view_slot=view_slot,
                report=snapshot.get("report"),
                history_by_code=snapshot.get("history_by_code"),
                product_names=snapshot.get("product_names"),
            ),
        }

    return {
        "card": product_template_callback_card(view_slot=view_slot, report_date=report_date),
    }
