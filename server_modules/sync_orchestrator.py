import json
import time
from datetime import datetime, timezone

from server_modules.sync_result import error_sync_result, normalized_sync_result


def sync_all_reelfarm_records(
    *,
    reelfarm_api_key,
    load_data,
    save_data,
    reelfarm_fetch_automations,
    product_code_for,
    build_country_automation_prefix,
    reelfarm_matches,
    reelfarm_creator_count,
    reelfarm_material_count,
    project_synced_country_to_relational,
    cleanup_reelfarm_product_from_latest_automations,
):
    if not reelfarm_api_key():
        raise RuntimeError("ReelFarm API key is not configured.")

    data = load_data()
    synced_at = datetime.now(timezone.utc).isoformat()
    automations = reelfarm_fetch_automations()
    successes = 0
    errors = []
    relational_projection = None
    product_cleanups = []

    for product in data:
        product_code = product_code_for(product)
        for country in product.get("countries", []) or []:
            prefix = build_country_automation_prefix(product, country)
            try:
                result = reelfarm_matches(prefix, automations=automations)
                country["reelFarmSyncedAt"] = synced_at
                country["creatorCount"] = reelfarm_creator_count(result)
                country["materialCount"] = reelfarm_material_count(result)
                scoped_country = dict(country)
                scoped_country["reelFarmResult"] = result
                relational_projection = project_synced_country_to_relational(product, scoped_country)
                successes += 1
            except RuntimeError as error:
                errors.append({"prefix": prefix, "error": str(error)})
        if product_code:
            try:
                product_cleanups.append(
                    cleanup_reelfarm_product_from_latest_automations(product_code, automations, synced_at)
                )
            except RuntimeError as error:
                errors.append({"product_code": product_code, "error": str(error)})

    save_data(data)
    return normalized_sync_result("reelfarm", {
        "ok": True,
        "synced_at": synced_at,
        "synced_count": successes,
        "error_count": len(errors),
        "errors": errors[:20],
        "product_cleanups": product_cleanups,
        "relational_projection": relational_projection,
    }, records_count=successes)


def sync_all_museon_clone_records(
    *,
    load_data,
    product_code_for,
    country_code_for,
    sync_museon_clone_country,
):
    data = load_data()
    successes = 0
    skipped = 0
    errors = []
    records = []

    for product in data:
        if not isinstance(product, dict):
            continue
        product_code = product_code_for(product)
        for country in product.get("countries") or []:
            if not isinstance(country, dict):
                continue
            country_code = country_code_for(country)
            try:
                result = sync_museon_clone_country(
                    str(product.get("id") or ""),
                    str(country.get("id") or ""),
                    product_code,
                    country_code,
                )
                records.append({
                    "product_code": product_code,
                    "country_code": country_code,
                    "creator_count": result.get("creator_count", 0),
                    "material_count": result.get("material_count", 0),
                    "post_count": result.get("post_count", 0),
                    "skipped": bool(result.get("skipped")),
                    "duration_total_seconds": result.get("duration_total_seconds"),
                })
                if result.get("skipped"):
                    skipped += 1
                else:
                    successes += 1
            except RuntimeError as error:
                errors.append({"product_code": product_code, "country_code": country_code, "error": str(error)})

    return normalized_sync_result("museon_clone", {
        "ok": True,
        "synced_count": successes,
        "skipped_count": skipped,
        "error_count": len(errors),
        "errors": errors[:20],
        "records": records[:50],
    }, records_count=successes)


def sync_all_growth_snapshots(*, configured_product_codes, sync_product_growth_snapshots, days=30):
    product_codes = configured_product_codes()

    successes = 0
    errors = []
    records = []
    for product_code in product_codes:
        try:
            product_records = sync_product_growth_snapshots(product_code, days)
            successes += 1
            records.append({"product_code": product_code, "count": len(product_records)})
        except (RuntimeError, ValueError) as error:
            errors.append({"product_code": product_code, "error": str(error)})

    return normalized_sync_result("growth_mixpanel", {
        "ok": True,
        "synced_count": successes,
        "error_count": len(errors),
        "errors": errors[:20],
        "records": records,
    }, records_count=successes)


def sync_daily_all_records(
    days=30,
    *,
    sync_all_reelfarm_records,
    sync_all_museon_clone_records,
    sync_all_growth_snapshots,
    safe_record_sync_run,
    sync_run_records_count,
    compact_sync_run_meta,
):
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    synced_at = datetime.now(timezone.utc).isoformat()
    stages = {}

    for stage_name, runner in (
        ("reelfarm", sync_all_reelfarm_records),
        ("museon_clone", sync_all_museon_clone_records),
        ("growth_mixpanel", lambda: sync_all_growth_snapshots(days)),
    ):
        stage_started = time.perf_counter()
        stage_started_at = datetime.now(timezone.utc).isoformat()
        try:
            payload = runner()
            duration = round(time.perf_counter() - stage_started, 3)
            stage_finished_at = datetime.now(timezone.utc).isoformat()
            payload = normalized_sync_result(
                stage_name,
                payload,
                started_at=stage_started_at,
                finished_at=stage_finished_at,
                duration_seconds=duration,
            )
            safe_record_sync_run(
                stage_name,
                "success" if payload.get("ok") else "error",
                stage_started_at,
                stage_finished_at,
                duration,
                records_count=sync_run_records_count(payload),
                error="" if payload.get("ok") else json.dumps(payload.get("errors") or payload.get("error") or "", ensure_ascii=False)[:1000],
                meta=compact_sync_run_meta(payload),
            )
            stages[stage_name] = payload
        except RuntimeError as error:
            duration = round(time.perf_counter() - stage_started, 3)
            stage_finished_at = datetime.now(timezone.utc).isoformat()
            safe_record_sync_run(
                stage_name,
                "error",
                stage_started_at,
                stage_finished_at,
                duration,
                error=str(error),
                meta={"error": str(error)},
            )
            stages[stage_name] = {
                **error_sync_result(
                    stage_name,
                    error,
                    started_at=stage_started_at,
                    finished_at=stage_finished_at,
                    duration_seconds=duration,
                )
            }

    ok = all(stage.get("ok") for stage in stages.values())
    duration_total = round(time.perf_counter() - started, 3)
    finished_at = datetime.now(timezone.utc).isoformat()
    result = normalized_sync_result("daily_all", {
        "ok": ok,
        "synced_at": synced_at,
        "timezone": "Asia/Shanghai",
        "schedule": "09:30 BJT",
        "duration_total_seconds": duration_total,
        "stages": stages,
    }, started_at=started_at, finished_at=finished_at, duration_seconds=duration_total)
    safe_record_sync_run(
        "daily_all",
        "success" if ok else "error",
        started_at,
        finished_at,
        duration_total,
        records_count=sync_run_records_count(result),
        error="" if ok else json.dumps({k: v.get("error") for k, v in stages.items() if not v.get("ok")}, ensure_ascii=False)[:1000],
        meta=compact_sync_run_meta(result),
    )
    return result
