import json
from datetime import datetime, timezone

from server_modules.app_runtime import load_app_value, save_app_value


SNAPSHOT_STATE_KEY = "feishu_daily_report_card_snapshots"
MAX_SNAPSHOTS = 50


def _empty_store():
    return {"latest_message_id": "", "snapshots": {}}


def load_snapshot_store():
    raw = load_app_value(SNAPSHOT_STATE_KEY)
    if not raw:
        return _empty_store()
    try:
        store = json.loads(raw)
    except json.JSONDecodeError:
        return _empty_store()
    if not isinstance(store, dict):
        return _empty_store()
    snapshots = store.get("snapshots")
    if not isinstance(snapshots, dict):
        snapshots = {}
    return {
        "latest_message_id": str(store.get("latest_message_id") or ""),
        "snapshots": snapshots,
    }


def save_daily_report_snapshot(message_id, *, report, history_by_code=None, product_names=None):
    message_id = str(message_id or "").strip()
    if not message_id:
        return None

    store = load_snapshot_store()
    snapshots = store.setdefault("snapshots", {})
    snapshots[message_id] = {
        "message_id": message_id,
        "report_date": str((report or {}).get("report_date") or ""),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "report": report or {},
        "history_by_code": history_by_code or {},
        "product_names": list(product_names or []),
    }
    store["latest_message_id"] = message_id

    ordered = sorted(
        snapshots.items(),
        key=lambda item: str((item[1] or {}).get("saved_at") or ""),
        reverse=True,
    )
    store["snapshots"] = dict(ordered[:MAX_SNAPSHOTS])
    save_app_value(SNAPSHOT_STATE_KEY, store)
    return store["snapshots"].get(message_id)


def load_daily_report_snapshot(message_id=""):
    store = load_snapshot_store()
    snapshots = store.get("snapshots") or {}
    message_id = str(message_id or "").strip()
    if message_id and message_id in snapshots:
        return snapshots.get(message_id)
    latest_message_id = str(store.get("latest_message_id") or "")
    if latest_message_id:
        return snapshots.get(latest_message_id)
    return None
