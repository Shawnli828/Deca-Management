import json
import time
from datetime import datetime, timezone

from server_modules.app_runtime import (
    connect_db,
    database_snapshot,
    default_data,
    init_relational_schema,
    load_data,
    save_data,
    using_postgres,
)
from server_modules.queries.ai_materials_query import ai_materials_payload as ai_materials_payload_impl
from server_modules.product_config import feishu_product_codes, growth_product_codes, product_registry
from server_modules.schema import relational_table_counts
from server_modules.services.data_enrichment import enrich_data_with_relational_rollups
from server_modules.services.data_query_runtime import data_query_payload as data_query_payload_impl
from server_modules.services import growth_runtime
from server_modules.services import sync_runtime
from server_modules.sync_result import normalized_sync_result


def enriched_data(data=None):
    return enrich_data_with_relational_rollups(load_data() if data is None else data)


def reset_data():
    data = default_data()
    save_data(data)
    return enriched_data(data)


def data_query_payload(query):
    return data_query_payload_impl(query)


def product_registry_payload():
    products = load_data()
    return {
        "ok": True,
        "products": product_registry(products),
        "growth_product_codes": growth_product_codes(products),
        "feishu_product_codes": feishu_product_codes(products),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def ai_materials_payload(query):
    return ai_materials_payload_impl(query)


def growth_dashboard_payload(query):
    return growth_runtime.growth_dashboard_payload(query)


def business_material_report_payload(query):
    return growth_runtime.business_material_report_payload(query)


def sync_product_growth_snapshots(product_code, days):
    return growth_runtime.sync_product_growth_snapshots(product_code, days)


def sync_party_a_growth_snapshots(days):
    return sync_products_growth_snapshots(growth_product_codes(load_data()), days)


def sync_products_growth_snapshots(product_codes, days):
    normalized_codes = []
    for product_code in product_codes or []:
        code = str(product_code or "").strip().upper()
        if code and code not in normalized_codes:
            normalized_codes.append(code)
    if not normalized_codes:
        raise ValueError("product_codes is required.")

    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    records = []
    errors = []
    snapshot_count = 0

    for product_code in normalized_codes:
        try:
            product_records = growth_runtime.sync_product_growth_snapshots(product_code, days)
            count = len(product_records)
            snapshot_count += count
            records.append({"product_code": product_code, "count": count})
        except (RuntimeError, ValueError) as error:
            errors.append({"product_code": product_code, "error": str(error)})

    duration = round(time.perf_counter() - started, 3)
    finished_at = datetime.now(timezone.utc).isoformat()
    ok = not errors and len(records) == len(normalized_codes)
    result = normalized_sync_result(
        "growth_mixpanel",
        {
            "ok": ok,
            "synced_count": len(records),
            "error_count": len(errors),
            "errors": errors[:20],
            "records": records,
            "product_codes": normalized_codes,
        },
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration,
        records_count=snapshot_count,
    )
    sync_runtime.safe_record_sync_run(
        "growth_mixpanel",
        "success" if ok else "error",
        started_at,
        finished_at,
        duration,
        records_count=snapshot_count,
        error="" if ok else json.dumps(errors[:20], ensure_ascii=False)[:1000],
        meta=sync_runtime.compact_sync_run_meta(result),
    )
    return result
