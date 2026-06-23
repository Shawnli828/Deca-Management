import json
from datetime import datetime, timedelta, timezone

from server_modules.app_runtime import load_app_value, save_app_value
from server_modules.daily_report import default_daily_report_date
from server_modules.metrics_service import daily_metric_windows
from server_modules.services.daily_feishu_runtime import (
    send_report,
    sync_readiness_payload,
    sync_status_payload,
)
from server_modules.time_windows import parse_iso_datetime


AUTO_SEND_STATE_KEY = "feishu_daily_report_auto_sends"
REQUIRED_SYNC_SOURCES = ("reelfarm", "museon_clone", "growth_mixpanel")
DEFAULT_SEND_DELAY_MINUTES = 20


def _load_auto_send_state():
    raw = load_app_value(AUTO_SEND_STATE_KEY)
    if not raw:
        return {"sent": {}}
    try:
        state = json.loads(raw)
    except json.JSONDecodeError:
        return {"sent": {}}
    if not isinstance(state, dict):
        return {"sent": {}}
    sent = state.get("sent")
    if not isinstance(sent, dict):
        sent = {}
    return {"sent": sent}


def _save_auto_send_state(state):
    sent = state.get("sent") if isinstance(state, dict) else {}
    if not isinstance(sent, dict):
        sent = {}
    ordered = sorted(
        sent.items(),
        key=lambda item: str((item[1] or {}).get("sent_at") or ""),
        reverse=True,
    )
    save_app_value(AUTO_SEND_STATE_KEY, {"sent": dict(ordered[:45])})


def _sync_window_end(report_date):
    windows = daily_metric_windows(report_date)
    return max(
        windows["content"]["utc_end"],
        windows["onboarding"]["utc_end"],
    )


def _latest_finished_at(sync_ready):
    latest = None
    for source in REQUIRED_SYNC_SOURCES:
        source_status = ((sync_ready or {}).get("sources") or {}).get(source) or {}
        finished = parse_iso_datetime(source_status.get("finished_at"))
        if finished and (latest is None or finished > latest):
            latest = finished
    return latest


def _template_message_ids(send_result):
    template_messages = (send_result or {}).get("template_messages") or {}
    return {
        "overview_message_id": template_messages.get("overview_message_id"),
    }


def auto_send_daily_feishu_report(
    report_date="",
    *,
    delay_minutes=DEFAULT_SEND_DELAY_MINUTES,
    mode="template",
    force=False,
    now=None,
):
    report_date = str(report_date or "").strip() or default_daily_report_date()
    mode = str(mode or "template").strip().lower()
    try:
        delay_minutes = max(0, int(delay_minutes))
    except (TypeError, ValueError):
        delay_minutes = DEFAULT_SEND_DELAY_MINUTES
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    state = _load_auto_send_state()
    existing = (state.get("sent") or {}).get(report_date)
    if existing and not force:
        return {
            "ok": True,
            "status": "already_sent",
            "sent": False,
            "report_date": report_date,
            "reason": "Daily Feishu report was already sent for this report date.",
            "existing": existing,
        }

    min_finished_at = _sync_window_end(report_date)
    sync_status = sync_status_payload()
    sync_ready = sync_readiness_payload(sync_status, min_finished_at.isoformat())
    if not sync_ready.get("ok"):
        return {
            "ok": True,
            "status": "waiting_for_sync",
            "sent": False,
            "report_date": report_date,
            "reason": "Required sync stages have not all finished for the report window.",
            "min_finished_at": min_finished_at.isoformat(),
            "sync_ready": sync_ready,
        }

    latest_finished = _latest_finished_at(sync_ready)
    if not latest_finished:
        return {
            "ok": True,
            "status": "waiting_for_sync",
            "sent": False,
            "report_date": report_date,
            "reason": "Required sync stages are ready but latest finished time is missing.",
            "min_finished_at": min_finished_at.isoformat(),
            "sync_ready": sync_ready,
        }

    send_after = latest_finished + timedelta(minutes=delay_minutes)
    if now < send_after and not force:
        return {
            "ok": True,
            "status": "waiting_delay",
            "sent": False,
            "report_date": report_date,
            "reason": f"Waiting until {delay_minutes} minutes after the last sync stage finishes.",
            "latest_sync_finished_at": latest_finished.isoformat(),
            "send_after": send_after.isoformat(),
            "sync_ready": sync_ready,
        }

    send_result = send_report(report_date, require_synced=True, mode=mode)
    if not send_result.get("ok"):
        return {
            "ok": False,
            "status": "send_failed",
            "sent": False,
            "report_date": report_date,
            "error": send_result.get("error") or "Failed to send Feishu daily report.",
            "send_result": send_result,
            "sync_ready": sync_ready,
        }

    sent_record = {
        "report_date": report_date,
        "sent_at": send_result.get("sent_at") or datetime.now(timezone.utc).isoformat(),
        "mode": send_result.get("mode") or mode,
        "latest_sync_finished_at": latest_finished.isoformat(),
        "send_after": send_after.isoformat(),
        "messages": _template_message_ids(send_result),
    }
    state.setdefault("sent", {})[report_date] = sent_record
    _save_auto_send_state(state)
    return {
        "ok": True,
        "status": "sent",
        "sent": True,
        "report_date": report_date,
        "sent_record": sent_record,
        "send_result": send_result,
        "sync_ready": sync_ready,
    }
