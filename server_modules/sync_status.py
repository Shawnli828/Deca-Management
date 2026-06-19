import json
from datetime import timezone

from server_modules.metrics_service import evaluate_sync_readiness


SYNC_RUN_SOURCE_LABELS = {
    "reelfarm": "RF",
    "museon_clone": "Clone",
    "growth_mixpanel": "Mixpanel",
    "daily_all": "全部同步",
}


def sync_run_records_count(payload):
    if not isinstance(payload, dict):
        return 0
    for key in ("synced_count", "count", "material_count", "post_count"):
        try:
            value = int(payload.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value:
            return value
    records = payload.get("records")
    if isinstance(records, list):
        return len(records)
    stages = payload.get("stages")
    if isinstance(stages, dict):
        return sum(sync_run_records_count(stage) for stage in stages.values())
    return 0


def record_sync_run_in_db(
    source,
    status,
    started_at,
    *,
    finished_at=None,
    duration_seconds=None,
    product_code="",
    country_code="",
    records_count=0,
    error="",
    meta=None,
    stable_id_fn,
    connect_db_fn,
    init_schema_fn,
    upsert_row_fn,
    now_fn,
):
    source = str(source or "").strip()
    if not source:
        return None
    started_at = str(started_at or now_fn(timezone.utc).isoformat())
    finished_at = str(finished_at or now_fn(timezone.utc).isoformat())
    try:
        records_count = int(records_count or 0)
    except (TypeError, ValueError):
        records_count = 0
    values = {
        "id": stable_id_fn("sync_run", source, product_code or "", country_code or "", started_at),
        "source": source,
        "product_code": str(product_code or "").strip().upper() or None,
        "country_code": str(country_code or "").strip().upper() or None,
        "status": str(status or "unknown"),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "records_count": records_count,
        "error": str(error or "")[:1000],
        "meta_json": json.dumps(meta or {}, ensure_ascii=False),
    }
    with connect_db_fn() as conn:
        init_schema_fn(conn)
        upsert_row_fn(conn, "sync_runs", values, ["id"])
        conn.commit()
    return values


def latest_sync_runs_from_db(
    *,
    sources=None,
    default_sources,
    placeholder,
    connect_db_fn,
    init_schema_fn,
    row_dict_fn,
):
    sources = list(sources or default_sources)
    if not sources:
        return {}
    with connect_db_fn() as conn:
        init_schema_fn(conn)
        result = {}
        for source in sources:
            row = conn.execute(
                f"""
                SELECT *
                FROM sync_runs
                WHERE source = {placeholder}
                ORDER BY COALESCE(finished_at, started_at) DESC
                LIMIT 1
                """,
                (source,),
            ).fetchone()
            result[source] = row_dict_fn(row) if row else None
        return result


def compact_sync_run_meta(payload):
    if not isinstance(payload, dict):
        return {}
    compact = {}
    for key in (
        "ok",
        "synced_count",
        "error_count",
        "duration_total_seconds",
        "product_cleanups",
    ):
        if key in payload:
            compact[key] = payload.get(key)
    errors = payload.get("errors")
    if isinstance(errors, list):
        compact["errors_preview"] = errors[:5]
    records = payload.get("records")
    if isinstance(records, list):
        compact["records_preview"] = records[:8]
        compact["records_count"] = len(records)
    return compact


def sync_status_from_runs(runs):
    runs = runs or {}
    return {
        "sources": {
            source: {
                "label": SYNC_RUN_SOURCE_LABELS.get(source, source),
                "status": (run or {}).get("status"),
                "started_at": (run or {}).get("started_at"),
                "finished_at": (run or {}).get("finished_at"),
                "duration_seconds": (run or {}).get("duration_seconds"),
                "records_count": (run or {}).get("records_count"),
                "error": (run or {}).get("error"),
            }
            for source, run in runs.items()
        }
    }


def sync_status_payload_from_runs(runs, generated_at):
    payload = sync_status_from_runs(runs)
    payload["generated_at"] = generated_at
    return payload


def format_sync_status_line(sync_status):
    if not isinstance(sync_status, dict):
        return "数据同步：暂无同步记录"
    parts = []
    for source in ("reelfarm", "museon_clone", "growth_mixpanel"):
        item = (sync_status.get("sources") or {}).get(source) or {}
        label = item.get("label") or SYNC_RUN_SOURCE_LABELS.get(source, source)
        finished_at = item.get("finished_at")
        status = item.get("status") or "unknown"
        if finished_at:
            parts.append(f"{label} {finished_at} ({status})")
        else:
            parts.append(f"{label} 暂无记录")
    return "数据同步：" + "；".join(parts)


def sync_readiness_payload(sync_status, min_finished_at):
    return evaluate_sync_readiness(
        sync_status,
        required_sources=("reelfarm", "museon_clone", "growth_mixpanel"),
        min_finished_at=min_finished_at,
    )


def format_sync_readiness_line(sync_ready):
    if not isinstance(sync_ready, dict):
        return "同步校验：暂无校验结果"
    if sync_ready.get("ok"):
        return "同步校验：RF / Clone / Mixpanel 已完成"
    warnings = sync_ready.get("warnings") or []
    if not warnings:
        return "同步校验：未通过"
    return "同步校验：" + "；".join(str(item) for item in warnings[:4])
