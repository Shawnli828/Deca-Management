from datetime import datetime, timezone


def sync_records_count(payload):
    if not isinstance(payload, dict):
        return 0
    if payload.get("records_count") is not None:
        try:
            return int(payload.get("records_count") or 0)
        except (TypeError, ValueError):
            return 0
    if isinstance(payload.get("records"), list):
        return len(payload.get("records") or [])
    if isinstance(payload.get("stages"), dict):
        return sum(sync_records_count(stage) for stage in payload.get("stages", {}).values())
    if payload.get("synced_count") is not None:
        try:
            return int(payload.get("synced_count") or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def normalized_sync_result(
    source,
    payload=None,
    *,
    product_code="",
    country_code="",
    started_at="",
    finished_at="",
    duration_seconds=None,
    records_count=None,
    error="",
):
    result = dict(payload or {})
    ok = bool(result.get("ok", not error))
    errors = result.get("errors")
    if errors is None:
        errors = []
    if error and not errors:
        errors = [{"error": str(error)}]

    result.setdefault("ok", ok)
    result.setdefault("source", source)
    result.setdefault("status", "success" if ok else "error")
    result.setdefault("product_code", str(product_code or result.get("product_code") or "").strip().upper())
    result.setdefault("country_code", str(country_code or result.get("country_code") or "").strip().upper())
    result.setdefault("started_at", started_at)
    result.setdefault("finished_at", finished_at)
    result.setdefault("synced_at", result.get("finished_at") or datetime.now(timezone.utc).isoformat())
    if duration_seconds is not None:
        result.setdefault("duration_seconds", duration_seconds)
        result.setdefault("duration_total_seconds", duration_seconds)
    else:
        result.setdefault("duration_seconds", result.get("duration_total_seconds"))
    result.setdefault("records_count", records_count if records_count is not None else sync_records_count(result))
    result["errors"] = errors
    if error:
        result.setdefault("error", str(error))
    return result


def error_sync_result(source, error, *, started_at="", finished_at="", duration_seconds=None):
    return normalized_sync_result(
        source,
        {"ok": False},
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        error=str(error),
    )
