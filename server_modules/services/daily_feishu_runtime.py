import os
from datetime import datetime, timezone

from server_modules.account_issues import daily_reelfarm_account_alerts as daily_reelfarm_account_alerts_impl
from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema, load_data, make_ssl_context
from server_modules.data_query_helpers import relational_base_from, row_dict
from server_modules.product_config import (
    configured_product_codes as configured_product_codes_impl,
    configured_product_name_map as configured_product_name_map_impl,
)
from server_modules.reelfarm_utils import reelfarm_expected_automation_condition
from server_modules.services.daily_feishu_service import DailyFeishuReportService
from server_modules.services.data_runtime import business_material_report_payload
from server_modules.settings import (
    FALLBACK_LLM_MODELS,
    FEISHU_WEBHOOK_SECRET,
    FEISHU_WEBHOOK_URL,
    LLM_API_BASE,
    LLM_MODEL,
    REPORT_TIMEZONE_NAME,
)
from server_modules.sync_status import (
    SYNC_RUN_SOURCE_LABELS,
    latest_sync_runs_from_db,
    sync_readiness_payload,
    sync_status_payload_from_runs,
)


def configured_product_codes():
    return configured_product_codes_impl(load_data())


def configured_product_name_map():
    return configured_product_name_map_impl(load_data())


def latest_sync_runs(sources=None):
    return latest_sync_runs_from_db(
        sources=sources,
        default_sources=SYNC_RUN_SOURCE_LABELS.keys(),
        placeholder=db_placeholder(),
        connect_db_fn=connect_db,
        init_schema_fn=init_relational_schema,
        row_dict_fn=row_dict,
    )


def sync_status_payload():
    runs = latest_sync_runs()
    return sync_status_payload_from_runs(runs, datetime.now(timezone.utc).isoformat())


def daily_reelfarm_account_alerts(product_code, utc_start, utc_end, limit=120):
    return daily_reelfarm_account_alerts_impl(
        product_code,
        utc_start,
        utc_end,
        limit=limit,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
        reelfarm_expected_automation_condition=reelfarm_expected_automation_condition,
    )


def product_reelfarm_country_avg_views(product_code, utc_start, utc_end):
    placeholder = db_placeholder()
    countries = {}
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                m.code AS country_code,
                m.name AS country_name,
                mat.id AS material_id,
                post.id AS post_id,
                COALESCE(post.view_count, 0) AS view_count
            {relational_base_from()}
            WHERE p.code = {placeholder}
              AND ch.code = {placeholder}
              AND {reelfarm_expected_automation_condition("a")}
              AND mat.id IS NOT NULL
              AND post.id IS NOT NULL
              AND mat.created_at >= {placeholder}
              AND mat.created_at < {placeholder}
            GROUP BY m.code, m.name, mat.id, post.id, post.view_count
            """,
            (
                str(product_code or "").upper(),
                "TIKTOK",
                utc_start.isoformat(),
                utc_end.isoformat(),
            ),
        ).fetchall()
    for row in rows:
        item = row_dict(row)
        country_code = str(item.get("country_code") or "").upper()
        if not country_code:
            continue
        entry = countries.setdefault(country_code, {
            "country_code": country_code,
            "country_name": item.get("country_name") or country_code,
            "material_ids": set(),
            "post_ids": set(),
            "views": 0,
        })
        if item.get("material_id"):
            entry["material_ids"].add(str(item.get("material_id")))
        if item.get("post_id"):
            entry["post_ids"].add(str(item.get("post_id")))
        entry["views"] += int(item.get("view_count") or 0)
    output = []
    for entry in countries.values():
        post_count = len(entry.get("material_ids") or set())
        views = int(entry.get("views") or 0)
        output.append({
            "country_code": entry.get("country_code"),
            "country_name": entry.get("country_name"),
            "reelfarm_posts": post_count,
            "reelfarm_views": views,
            "reelfarm_avg_views": (views / post_count) if post_count else None,
        })
    return sorted(output, key=lambda row: (row.get("country_name") or row.get("country_code") or ""))


def daily_feishu_service():
    return DailyFeishuReportService(
        env=os.environ,
        webhook_url=os.environ.get("FEISHU_WEBHOOK_URL", "").strip() or FEISHU_WEBHOOK_URL,
        webhook_secret=os.environ.get("FEISHU_WEBHOOK_SECRET", "").strip() or FEISHU_WEBHOOK_SECRET,
        llm_api_base=os.environ.get("LLM_API_BASE", "").strip().rstrip("/") or LLM_API_BASE,
        llm_model=LLM_MODEL,
        fallback_llm_models=FALLBACK_LLM_MODELS,
        report_timezone_name=REPORT_TIMEZONE_NAME,
        make_ssl_context=make_ssl_context,
        configured_product_codes=configured_product_codes,
        configured_product_name_map=configured_product_name_map,
        business_material_report_payload=business_material_report_payload,
        daily_reelfarm_account_alerts=daily_reelfarm_account_alerts,
        product_reelfarm_country_avg_views=product_reelfarm_country_avg_views,
        sync_status_payload=sync_status_payload,
        sync_readiness_payload=sync_readiness_payload,
    )


def report_payload(report_date=""):
    return daily_feishu_service().report_payload(report_date)


def ai_analysis(report_date="", model="", report=None, require_config=False):
    return daily_feishu_service().ai_analysis(report_date, model, report, require_config)


def llm_models_payload():
    return daily_feishu_service().llm_models_payload()


def send_report(report_date="", include_ai=False, model="", require_synced=False):
    return daily_feishu_service().send_report(report_date, include_ai, model, require_synced)
