from datetime import datetime, timedelta, timezone

from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema, make_ssl_context
from server_modules.common import stable_id
from server_modules.data_query_helpers import query_value, relational_base_from, row_dict
from server_modules.db_core import upsert_row as upsert_row_impl
from server_modules.domain.growth import business_growth_daily_stats_from_snapshots
from server_modules.growth_report_service import (
    business_material_report_payload as business_material_report_payload_impl,
    growth_dashboard_payload as growth_dashboard_payload_impl,
)
from server_modules.metrics_service import (
    business_report_windows_with_onboarding,
    normalize_business_report_row,
    summarize_business_report_rows,
)
from server_modules.mixpanel_client import (
    mixpanel_event_business_material_counts as mixpanel_event_business_material_counts_impl,
    mixpanel_event_daily_counts as mixpanel_event_daily_counts_impl,
    mixpanel_event_user_unique_query_count as mixpanel_event_user_unique_query_count_impl,
)
from server_modules.mixpanel_utils import product_mixpanel_config, product_mixpanel_event_name
from server_modules.repositories import growth_repository
from server_modules.reelfarm_utils import (
    reelfarm_expected_automation_condition,
    reelfarm_schedule_slot_count,
)
from server_modules.settings import MIXPANEL_REGION, MIXPANEL_TIMEZONE_NAME, REPORT_TIMEZONE_NAME
from server_modules.time_windows import (
    business_material_date_for_utc_datetime,
    growth_report_windows,
    mixpanel_timezone,
    onboarding_date_for_utc_datetime,
    onboarding_day_window,
    parse_iso_datetime,
    report_date_for_utc_datetime,
    report_day_window,
    report_timezone,
    source_dates_for_utc_window,
)


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


def product_channel_views_for_window(product_code, channel_code, utc_start, utc_end):
    return growth_repository.product_channel_views_for_window(product_code, channel_code, utc_start, utc_end)


def product_channel_daily_views(product_code, channel_code, utc_start, utc_end):
    return growth_repository.product_channel_daily_views(product_code, channel_code, utc_start, utc_end)


def product_business_material_daily_stats(product_code, utc_start, utc_end):
    return growth_repository.product_business_material_daily_stats(product_code, utc_start, utc_end)


def product_active_reelfarm_expected_automation_count(product_code):
    return growth_repository.product_active_reelfarm_expected_automation_count(product_code)


def product_active_reelfarm_expected_schedule_count(product_code):
    return growth_repository.product_active_reelfarm_expected_schedule_count(product_code)


def latest_snapshot_views_by_source(product_code, snapshot_date):
    return growth_repository.latest_snapshot_views_by_source(product_code, snapshot_date)


def product_growth_download_daily(product_code, date_from, date_to):
    return growth_repository.product_growth_download_daily(product_code, date_from, date_to)


def product_business_growth_daily_stats(product_code, windows):
    if not windows:
        return {}
    needed_dates = set()
    for window in windows:
        report_date = str(window["report_date"])
        previous_date = (datetime.strptime(report_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
        needed_dates.add(report_date)
        needed_dates.add(previous_date)
    snapshot_cache = {
        snapshot_date: latest_snapshot_views_by_source(product_code, snapshot_date)
        for snapshot_date in sorted(needed_dates)
    }
    return business_growth_daily_stats_from_snapshots(windows, snapshot_cache)


def mixpanel_event_daily_counts(config, event_name, utc_start, utc_end, value_type="general"):
    return mixpanel_event_daily_counts_impl(
        config,
        event_name,
        utc_start,
        utc_end,
        value_type,
        default_region=MIXPANEL_REGION,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        report_date_for_utc_datetime=report_date_for_utc_datetime,
        make_ssl_context=make_ssl_context,
    )


def mixpanel_event_user_unique_query_count(config, event_name, utc_start, utc_end):
    return mixpanel_event_user_unique_query_count_impl(
        config,
        event_name,
        utc_start,
        utc_end,
        default_region=MIXPANEL_REGION,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        make_ssl_context=make_ssl_context,
    )


def mixpanel_event_onboarding_daily_counts(config, event_name, utc_start, utc_end):
    return mixpanel_event_business_material_counts_impl(
        config,
        event_name,
        utc_start,
        utc_end,
        "unique",
        date_mapper=onboarding_date_for_utc_datetime,
        default_region=MIXPANEL_REGION,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        business_material_date_for_utc_datetime=business_material_date_for_utc_datetime,
        make_ssl_context=make_ssl_context,
    )


def mixpanel_event_total(config, event_name, utc_start, utc_end, value_type="general"):
    daily = mixpanel_event_daily_counts(config, event_name, utc_start, utc_end, value_type)
    if not daily and not (config or {}).get("project_id"):
        return None
    return sum(int(value or 0) for value in daily.values())


def sync_product_growth_snapshot(product_code, report_date=""):
    product_code = str(product_code or "").strip().upper()
    if not product_code:
        raise ValueError("product_code is required.")
    window = report_day_window(report_date)
    source_tz = mixpanel_timezone()
    source_date_from, source_date_to = source_dates_for_utc_window(window["utc_start"], window["utc_end"], source_tz)
    rf = product_channel_views_for_window(product_code, "TIKTOK", window["utc_start"], window["utc_end"])
    clone = product_channel_views_for_window(product_code, "MUSEON_CLONE", window["utc_start"], window["utc_end"])
    mixpanel_config = product_mixpanel_config(product_code)
    onboarding_event = product_mixpanel_event_name(product_code, "ONBOARDING")
    onboarding_window = onboarding_day_window(window["report_date"])
    onboarding_unique = mixpanel_event_user_unique_query_count(
        mixpanel_config,
        onboarding_event,
        onboarding_window["utc_start"],
        onboarding_window["utc_end"],
    )
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": stable_id("product_daily_growth_snapshot", product_code, window["report_date"]),
        "product_code": product_code,
        "report_date": window["report_date"],
        "report_timezone": window["report_timezone"],
        "source_timezone": getattr(source_tz, "key", MIXPANEL_TIMEZONE_NAME),
        "utc_start": window["utc_start"].isoformat(),
        "utc_end": window["utc_end"].isoformat(),
        "source_date_from": source_date_from,
        "source_date_to": source_date_to,
        "reelfarm_views": rf["views"],
        "clone_views": clone["views"],
        "total_views": rf["views"] + clone["views"],
        "download_count": None,
        "onboarding_unique": onboarding_unique,
        "synced_at": now,
    }
    return growth_repository.upsert_product_daily_growth_snapshot(record)


def sync_product_growth_snapshots(product_code, days=30):
    product_code = str(product_code or "").strip().upper()
    if not product_code:
        raise ValueError("product_code is required.")
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 30
    days = max(1, min(90, days))
    windows = growth_report_windows(days)
    if not windows:
        return []
    overall_utc_start = windows[0]["utc_start"]
    overall_utc_end = windows[-1]["utc_end"]
    source_tz = mixpanel_timezone()
    rf_daily = product_channel_daily_views(product_code, "TIKTOK", overall_utc_start, overall_utc_end)
    clone_daily = product_channel_daily_views(product_code, "MUSEON_CLONE", overall_utc_start, overall_utc_end)
    mixpanel_config = product_mixpanel_config(product_code)
    onboarding_event = product_mixpanel_event_name(product_code, "ONBOARDING")
    onboarding_windows = {
        window["report_date"]: onboarding_day_window(window["report_date"])
        for window in windows
    }
    onboarding_daily = mixpanel_event_onboarding_daily_counts(
        mixpanel_config,
        onboarding_event,
        onboarding_windows[windows[0]["report_date"]]["utc_start"],
        onboarding_windows[windows[-1]["report_date"]]["utc_end"],
    )
    now = datetime.now(timezone.utc).isoformat()
    records = []
    for window in windows:
        report_date = window["report_date"]
        source_date_from, source_date_to = source_dates_for_utc_window(window["utc_start"], window["utc_end"], source_tz)
        reelfarm_views = int(rf_daily.get(report_date) or 0)
        clone_views = int(clone_daily.get(report_date) or 0)
        record = {
            "id": stable_id("product_daily_growth_snapshot", product_code, report_date),
            "product_code": product_code,
            "report_date": report_date,
            "report_timezone": window["report_timezone"],
            "source_timezone": getattr(source_tz, "key", MIXPANEL_TIMEZONE_NAME),
            "utc_start": window["utc_start"].isoformat(),
            "utc_end": window["utc_end"].isoformat(),
            "source_date_from": source_date_from,
            "source_date_to": source_date_to,
            "reelfarm_views": reelfarm_views,
            "clone_views": clone_views,
            "total_views": reelfarm_views + clone_views,
            "download_count": None,
            "onboarding_unique": onboarding_daily.get(report_date),
            "synced_at": now,
        }
        records.append(record)
    growth_repository.upsert_product_daily_growth_snapshots(records)
    return records


def growth_dashboard_payload(query):
    return growth_dashboard_payload_impl(
        query,
        query_value=query_value,
        report_timezone=report_timezone,
        db_placeholder=db_placeholder,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        row_dict=row_dict,
        report_timezone_name=REPORT_TIMEZONE_NAME,
        mixpanel_timezone_name=MIXPANEL_TIMEZONE_NAME,
    )


def business_material_report_payload(query):
    return business_material_report_payload_impl(
        query,
        query_value=query_value,
        business_report_windows_with_onboarding=business_report_windows_with_onboarding,
        product_business_material_daily_stats=product_business_material_daily_stats,
        product_business_growth_daily_stats=product_business_growth_daily_stats,
        product_active_reelfarm_expected_automation_count=product_active_reelfarm_expected_automation_count,
        product_growth_download_daily=product_growth_download_daily,
        normalize_business_report_row=normalize_business_report_row,
        summarize_business_report_rows=summarize_business_report_rows,
        report_timezone_name=REPORT_TIMEZONE_NAME,
        mixpanel_timezone_name=MIXPANEL_TIMEZONE_NAME,
    )
