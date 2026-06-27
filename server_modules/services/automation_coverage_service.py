from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from server_modules.repositories import automation_coverage_repository as repository


READY_STATUSES = {"ready", "completed"}
CLOSED_STATUSES = {"activated", "cancelled"}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _format_date(value: date | None) -> str:
    return value.isoformat() if value else ""


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def _completion(active_count: int, target_count: int) -> float | None:
    if target_count <= 0:
        return None
    return round(_clamp(active_count / target_count * 100), 1)


def _warmup_progress(start_date: date | None, warmup_days: int, today: date) -> float:
    if not start_date or warmup_days <= 0:
        return 0
    elapsed_days = (today - start_date).days
    return round(_clamp(elapsed_days / warmup_days * 100), 1)


def _normalize_warmup_batch(raw: dict[str, Any], today: date) -> dict[str, Any]:
    account_count = max(int(raw.get("account_count") or 0), 0)
    warmup_days = max(int(raw.get("warmup_days") or 7), 1)
    start_date = _parse_date(raw.get("warmup_start_date"))
    end_date = _parse_date(raw.get("warmup_end_date"))
    if start_date and not end_date:
        end_date = start_date + timedelta(days=warmup_days)

    status = str(raw.get("status") or "warming").strip().lower() or "warming"
    remaining_days = max((end_date - today).days, 0) if end_date else None
    progress = _warmup_progress(start_date, warmup_days, today)
    if status == "warming" and end_date and end_date <= today:
        status = "ready"
        progress = 100

    return {
        "id": raw.get("id"),
        "product_code": str(raw.get("product_code") or "").upper(),
        "country_code": str(raw.get("country_code") or "").upper(),
        "batch_name": raw.get("batch_name") or "",
        "account_count": account_count,
        "warmup_start_date": _format_date(start_date),
        "warmup_days": warmup_days,
        "warmup_end_date": _format_date(end_date),
        "remaining_days": remaining_days,
        "progress": progress,
        "status": status,
        "note": raw.get("note") or "",
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
    }


def _country_status(
    active_count: int,
    target_count: int,
    ready_count: int,
    warming_count: int,
) -> str:
    if target_count <= 0:
        return "unset"
    if active_count >= target_count:
        return "achieved"
    if active_count + ready_count >= target_count:
        return "ready_to_cover"
    if active_count + ready_count + warming_count >= target_count:
        return "warming_to_cover"
    if active_count / target_count < 0.5:
        return "critical"
    return "behind"


def _warmup_summary(batches: list[dict[str, Any]]) -> dict[str, Any]:
    warming = [batch for batch in batches if batch["status"] not in READY_STATUSES | CLOSED_STATUSES]
    ready = [batch for batch in batches if batch["status"] in READY_STATUSES]
    warming_count = sum(batch["account_count"] for batch in warming)
    ready_count = sum(batch["account_count"] for batch in ready)
    total_accounts = sum(batch["account_count"] for batch in warming)
    if total_accounts > 0:
        progress = round(
            sum(batch["progress"] * batch["account_count"] for batch in warming) / total_accounts,
            1,
        )
    elif ready_count > 0:
        progress = 100
    else:
        progress = 0

    next_ready = min((batch["warmup_end_date"] for batch in warming if batch["warmup_end_date"]), default="")
    next_ready_days = min(
        (batch["remaining_days"] for batch in warming if batch["remaining_days"] is not None),
        default=None,
    )
    return {
        "warming_count": warming_count,
        "ready_count": ready_count,
        "progress": progress,
        "next_ready_date": next_ready,
        "next_ready_days": next_ready_days,
    }


def get_automation_coverage_payload() -> dict[str, Any]:
    today = _today()
    count_rows = repository.fetch_product_country_automation_counts()
    target_rows = repository.fetch_targets()
    warmup_rows = repository.fetch_warmup_batches(include_closed=False)

    targets = {
        (str(row.get("product_code") or "").upper(), str(row.get("country_code") or "").upper()): row
        for row in target_rows
    }
    warmups_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in warmup_rows:
        batch = _normalize_warmup_batch(row, today)
        key = (batch["product_code"], batch["country_code"])
        warmups_by_key[key].append(batch)

    products: dict[str, dict[str, Any]] = {}
    for row in count_rows:
        product_code = str(row.get("product_code") or "").upper()
        country_code = str(row.get("country_code") or "").upper()
        if not product_code or not country_code:
            continue
        product = products.setdefault(
            product_code,
            {
                "product_id": row.get("product_id"),
                "product_code": product_code,
                "product_name": row.get("product_name") or product_code,
                "logo_url": row.get("logo_url") or "",
                "active_count": 0,
                "target_count": 0,
                "gap_count": 0,
                "surplus_count": 0,
                "warming_count": 0,
                "ready_count": 0,
                "completion_rate": None,
                "countries": [],
                "warmups": [],
            },
        )

        key = (product_code, country_code)
        target = targets.get(key) or {}
        target_count = max(int(target.get("target_count") or 0), 0)
        active_count = max(int(row.get("active_count") or 0), 0)
        warmup_summary = _warmup_summary(warmups_by_key.get(key, []))
        gap_count = max(target_count - active_count, 0) if target_count > 0 else 0
        surplus_count = max(active_count - target_count, 0) if target_count > 0 else 0
        country = {
            "country_id": row.get("country_id"),
            "country_code": country_code,
            "country_name": row.get("country_name") or country_code,
            "active_count": active_count,
            "target_count": target_count,
            "gap_count": gap_count,
            "surplus_count": surplus_count,
            "completion_rate": _completion(active_count, target_count),
            "warming_count": warmup_summary["warming_count"],
            "ready_count": warmup_summary["ready_count"],
            "warmup_progress": warmup_summary["progress"],
            "next_ready_date": warmup_summary["next_ready_date"],
            "next_ready_days": warmup_summary["next_ready_days"],
            "status": _country_status(
                active_count,
                target_count,
                warmup_summary["ready_count"],
                warmup_summary["warming_count"],
            ),
            "target_note": target.get("note") or "",
            "warmups": warmups_by_key.get(key, []),
        }
        product["countries"].append(country)
        product["active_count"] += active_count
        product["target_count"] += target_count
        product["warming_count"] += warmup_summary["warming_count"]
        product["ready_count"] += warmup_summary["ready_count"]
        product["warmups"].extend(warmups_by_key.get(key, []))

    for product in products.values():
        product["countries"].sort(key=lambda country: (country["status"] == "achieved", -country["gap_count"], country["country_name"]))
        product["gap_count"] = max(product["target_count"] - product["active_count"], 0) if product["target_count"] > 0 else 0
        product["surplus_count"] = max(product["active_count"] - product["target_count"], 0) if product["target_count"] > 0 else 0
        product["completion_rate"] = _completion(product["active_count"], product["target_count"])

    product_list = sorted(
        products.values(),
        key=lambda product: (product["product_name"].lower(), product["product_code"]),
    )
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "products": product_list,
    }


def save_automation_target(product_code: str, country_code: str, target_count: int, note: str = "") -> dict[str, Any]:
    repository.upsert_target(product_code, country_code, target_count, note)
    return get_automation_coverage_payload()


def create_warmup_batch(record: dict[str, Any]) -> dict[str, Any]:
    warmup_days = max(int(record.get("warmup_days") or 7), 1)
    start_date = _parse_date(record.get("warmup_start_date")) or _today()
    end_date = start_date + timedelta(days=warmup_days)
    repository.insert_warmup_batch(
        {
            **record,
            "warmup_start_date": start_date.isoformat(),
            "warmup_days": warmup_days,
            "warmup_end_date": end_date.isoformat(),
            "status": record.get("status") or "warming",
        }
    )
    return get_automation_coverage_payload()


def update_warmup_batch(batch_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    clean_updates = dict(updates)
    if "warmup_start_date" in clean_updates or "warmup_days" in clean_updates:
        current = repository.fetch_warmup_batch(batch_id) or {}
        start_date = _parse_date(clean_updates.get("warmup_start_date") or current.get("warmup_start_date")) or _today()
        warmup_days = max(int(clean_updates.get("warmup_days") or current.get("warmup_days") or 7), 1)
        clean_updates["warmup_start_date"] = start_date.isoformat()
        clean_updates["warmup_days"] = warmup_days
        clean_updates["warmup_end_date"] = (start_date + timedelta(days=warmup_days)).isoformat()
    repository.update_warmup_batch(batch_id, clean_updates)
    return get_automation_coverage_payload()
