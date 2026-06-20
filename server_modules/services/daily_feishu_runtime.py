import os
from datetime import datetime, timezone

from server_modules.account_issues import daily_reelfarm_account_alerts as daily_reelfarm_account_alerts_impl
from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema, load_data, make_ssl_context
from server_modules.data_query_helpers import row_dict
from server_modules.product_config import (
    configured_product_codes as configured_product_codes_impl,
    configured_product_name_map as configured_product_name_map_impl,
)
from server_modules.repositories.daily_feishu_repository import (
    product_reelfarm_country_avg_views as product_reelfarm_country_avg_views_from_db,
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
    return product_reelfarm_country_avg_views_from_db(product_code, utc_start, utc_end)


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


def report_card_data(report_date="", report=None):
    return daily_feishu_service().report_card_data(report_date, report)


def report_card(report_date="", report=None):
    return daily_feishu_service().report_card(report_date, report)


def report_template_variables(report_date="", report=None, view_slot="product_1"):
    return daily_feishu_service().report_template_variables(report, report_date, view_slot)


def ai_analysis(report_date="", model="", report=None, require_config=False):
    return daily_feishu_service().ai_analysis(report_date, model, report, require_config)


def llm_models_payload():
    return daily_feishu_service().llm_models_payload()


def send_report(report_date="", include_ai=False, model="", require_synced=False, mode="text"):
    return daily_feishu_service().send_report(report_date, include_ai, model, require_synced, mode)


def product_template_callback_card(
    view_slot="product_1",
    report_date="",
    report=None,
    history_by_code=None,
    product_names=None,
):
    return daily_feishu_service().product_template_callback_card(
        view_slot,
        report_date,
        report=report,
        history_by_code=history_by_code,
        product_names=product_names,
    )
