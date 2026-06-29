#!/usr/bin/env python3
import os
import re
from datetime import datetime, timedelta, timezone

from server_modules.time_windows import (
    BUSINESS_TIMEZONE,
    business_date_string,
    business_material_date_for_utc_datetime,
    business_material_day_window,
    business_material_report_windows,
    growth_report_windows,
    mixpanel_timezone,
    onboarding_day_window,
    parse_iso_datetime,
    previous_complete_windows,
    report_date_for_utc_datetime,
    report_day_window,
    report_timezone,
    source_dates_for_utc_window,
    utc_date_string,
)
from server_modules.metrics_service import (
    business_report_windows_with_onboarding,
    normalize_business_report_row,
    normalize_reelfarm_account_row,
    summarize_business_report_rows,
)
from server_modules.growth_report_service import (
    business_material_report_payload as business_material_report_payload_impl,
    growth_dashboard_payload as growth_dashboard_payload_impl,
)
from server_modules.services.daily_feishu_service import DailyFeishuReportService
from server_modules.sync_status import (
    SYNC_RUN_SOURCE_LABELS,
    compact_sync_run_meta,
    latest_sync_runs_from_db,
    record_sync_run_in_db,
    sync_readiness_payload,
    sync_run_records_count,
    sync_status_payload_from_runs,
)
from server_modules.sync_orchestrator import (
    sync_all_growth_snapshots as sync_all_growth_snapshots_impl,
    sync_all_museon_clone_records as sync_all_museon_clone_records_impl,
    sync_all_reelfarm_records as sync_all_reelfarm_records_impl,
    sync_daily_all_records as sync_daily_all_records_impl,
)
from server_modules.reelfarm_utils import (
    reelfarm_automation_is_active as reelfarm_automation_is_active_impl,
    reelfarm_dashboard_automation_condition as reelfarm_dashboard_automation_condition_impl,
    reelfarm_expected_automation_condition as reelfarm_expected_automation_condition_impl,
    reelfarm_post_as_draft_value,
    reelfarm_post_mode,
    reelfarm_publish_method,
    reelfarm_schedule_slot_count,
)
from server_modules.reelfarm_client import (
    reelfarm_creator_count as reelfarm_creator_count_impl,
    reelfarm_fetch_automations as reelfarm_fetch_automations_impl,
    reelfarm_matches as reelfarm_matches_impl,
    reelfarm_material_count as reelfarm_material_count_impl,
    reelfarm_request as reelfarm_request_impl,
)
from server_modules.reelfarm_lifecycle import (
    active_tiktok_automation_account_ids as active_tiktok_automation_account_ids_impl,
    cleanup_reelfarm_product_from_latest_automations as cleanup_reelfarm_product_from_latest_automations_impl,
    mark_missing_reelfarm_automations as mark_missing_reelfarm_automations_impl,
)
from server_modules.automation_naming import (
    build_automation_prefix,
    build_country_automation_prefix,
    parse_concept_format_from_automation,
    prefixes_equivalent,
)
from server_modules.museon_utils import (
    museon_account_from_post,
    museon_content_id_from_material_source,
    museon_post_images,
    museon_post_metrics,
)
from server_modules.museon_client import (
    museon_all_posts as museon_all_posts_impl,
    museon_campaigns as museon_campaigns_impl,
    museon_clone_campaign as museon_clone_campaign_impl,
    museon_clone_campaigns_for_product as museon_clone_campaigns_for_product_impl,
    museon_content_download_images as museon_content_download_images_impl,
    museon_posts as museon_posts_impl,
    museon_request as museon_request_impl,
)
from server_modules.mixpanel_utils import (
    mixpanel_segmentation_unique_from_payload,
    product_mixpanel_config,
    product_mixpanel_event_name,
)
from server_modules.mixpanel_client import (
    mixpanel_event_business_material_counts as mixpanel_event_business_material_counts_impl,
    mixpanel_event_daily_counts as mixpanel_event_daily_counts_impl,
    mixpanel_event_user_unique_query_count as mixpanel_event_user_unique_query_count_impl,
)
from server_modules.app_runtime import (
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
    AI_API_KEY,
    BASE_DIR,
    DB_PATH,
    DATABASE_URL,
    EXTERNAL_API_KEYS_KEY,
    REELFARM_API_KEY,
    SEED_DATA_PATH,
    SESSION_COOKIE,
    SESSION_SECRET,
    SESSION_TTL_SECONDS,
    STATE_KEY,
    connect_db,
    data_source_channel_code,
    database_snapshot as database_snapshot_runtime,
    db_placeholder,
    default_data,
    delete_app_value,
    init_db,
    init_relational_schema,
    initial_data,
    load_app_value,
    load_data,
    make_auth_token as make_auth_token_runtime,
    make_ssl_context,
    reset_schema_init_cache,
    save_app_value,
    save_data,
    strip_reelfarm_state,
    using_postgres,
    valid_auth_token as valid_auth_token_runtime,
)
from server_modules.services.api_key_runtime import (
    authorized as external_api_key_authorized_runtime,
    create as create_external_api_key_runtime,
    list_keys as list_external_api_keys_runtime,
    load_keys as load_external_api_keys_runtime,
    revoke as revoke_external_api_key_runtime,
    save_keys as save_external_api_keys_runtime,
)
from server_modules.account_issues import (
    ZERO_PLAY_ISSUE,
    ZERO_PLAY_POST_LIMIT,
    ZERO_PLAY_VIEW_THRESHOLD,
    account_alert_display_name as account_alert_display_name_impl,
    account_issues_payload as account_issues_payload_impl,
    add_account_issue as add_account_issue_impl,
    apply_zero_play_issues as apply_zero_play_issues_impl,
    attach_account_issues as attach_account_issues_impl,
    collect_zero_play_issue_candidate as collect_zero_play_issue_candidate_impl,
    daily_reelfarm_account_alerts as daily_reelfarm_account_alerts_impl,
    delete_account_issue as delete_account_issue_impl,
)
from server_modules.tags import (
    account_tags_payload as account_tags_payload_impl,
    add_account_tag as add_account_tag_impl,
    clean_tag as clean_tag_impl,
    create_product_tag as create_product_tag_impl,
    delete_account_tag as delete_account_tag_impl,
    delete_product_tag as delete_product_tag_impl,
    existing_tag_value as existing_tag_value_impl,
    product_tags_payload as product_tags_payload_impl,
)
from server_modules.data_query_helpers import (
    common_where as common_where_impl,
    compact_filters as compact_filters_impl,
    pagination_payload as pagination_payload_impl,
    post_datetime_bound as post_datetime_bound_impl,
    query_days_snapshot_window as query_days_snapshot_window_impl,
    query_days_window as query_days_window_impl,
    query_filters as query_filters_impl,
    query_limit_offset as query_limit_offset_impl,
    query_value as query_value_impl,
    relational_base_from as relational_base_from_impl,
    row_dict as row_dict_impl,
)
from server_modules.detailed_rows import (
    detailed_row as detailed_row_impl,
    detailed_select as detailed_select_impl,
)
from server_modules.services.data_query_runtime import (
    data_query_payload as data_query_payload_runtime,
    query_accounts as query_accounts_runtime,
    query_materials as query_materials_runtime,
    query_posts as query_posts_runtime,
)
from server_modules.queries.ai_materials_query import ai_materials_payload as ai_materials_payload_runtime
from server_modules.queries.read_model_queries import (
    query_countries as query_countries_runtime,
    query_country_cards as query_country_cards_runtime,
    query_daily_metrics as query_daily_metrics_runtime,
    query_product_kpis as query_product_kpis_runtime,
    query_product_rollups as query_product_rollups_runtime,
    query_summary as query_summary_runtime,
    stored_reelfarm_country as stored_reelfarm_country_runtime,
)
from server_modules.services.data_enrichment import (
    enrich_data_with_relational_rollups as enrich_data_with_relational_rollups_runtime,
)
from server_modules.services import (
    daily_feishu_runtime,
    growth_runtime,
    museon_runtime,
    reelfarm_projection_runtime,
    sync_runtime,
)
from server_modules.auth_utils import (
    cookie_header,
    cron_authorized as cron_secret_authorized,
    password_hash,
)
from server_modules.common import (
    code_from_name,
    db_json,
    generate_id,
    int_or_none,
    normalize_username,
    parse_json_list,
    readable_utc_datetime,
    stable_id,
    utc_snapshot_date,
)
from server_modules.schema import (
    relational_table_counts as relational_table_counts_impl,
)
from server_modules.product_config import (
    COUNTRY_CODES,
    configured_product_codes as configured_product_codes_impl,
    configured_product_name_map as configured_product_name_map_impl,
    country_code_for,
    product_code_for,
    product_country_lookup as product_country_lookup_impl,
)
from server_modules.db_core import (
    upsert_row as upsert_row_impl,
)


REELFARM_BASE_URL = "https://reel.farm/api/v1"
MUSEON_BASE_URL = os.environ.get("MUSEON_BASE_URL", "https://api.museon.ai/external/api/v1").strip().rstrip("/")
MUSEON_API_KEY = os.environ.get("MUSEON_API_KEY", "").strip()
MUSEON_WORKSPACE_ID = os.environ.get("MUSEON_WORKSPACE_ID", "b5e25f84-b3ed-484b-b467-901a4afcd9c6").strip()
MUSEON_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
MIXPANEL_REGION = os.environ.get("MIXPANEL_REGION", "standard").strip().lower()
REPORT_TIMEZONE_NAME = os.environ.get("REPORT_TIMEZONE", "Asia/Shanghai").strip()
MIXPANEL_TIMEZONE_NAME = os.environ.get("MIXPANEL_TIMEZONE", "America/Los_Angeles").strip()
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
FEISHU_WEBHOOK_SECRET = os.environ.get("FEISHU_WEBHOOK_SECRET", "").strip()


def normalized_catalog_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def relational_catalog_code_maps():
    product_codes_by_name = {}
    market_codes_by_product_and_name = {}
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            """
            SELECT DISTINCT
                p.code AS product_code,
                p.name AS product_name,
                m.code AS market_code,
                m.name AS market_name
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            WHERE ch.code = 'TIKTOK'
            """
        ).fetchall()
    for row in rows:
        product_code = str(row["product_code"] or "").upper()
        market_code = str(row["market_code"] or "").upper()
        product_name_key = normalized_catalog_name(row["product_name"])
        market_name_key = normalized_catalog_name(row["market_name"])
        if product_code and product_name_key:
            product_codes_by_name[product_name_key] = product_code
        if product_code and market_code and market_name_key:
            market_codes_by_product_and_name[(product_code, market_name_key)] = market_code
    return product_codes_by_name, market_codes_by_product_and_name


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


def record_sync_run(source, status, started_at, finished_at=None, duration_seconds=None, product_code="", country_code="", records_count=0, error="", meta=None):
    return record_sync_run_in_db(
        source,
        status,
        started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        product_code=product_code,
        country_code=country_code,
        records_count=records_count,
        error=error,
        meta=meta,
        stable_id_fn=stable_id,
        connect_db_fn=connect_db,
        init_schema_fn=init_relational_schema,
        upsert_row_fn=upsert_row,
        now_fn=datetime.now,
    )


def safe_record_sync_run(*args, **kwargs):
    try:
        return record_sync_run(*args, **kwargs)
    except Exception as error:
        return {"error": str(error)}


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


def reelfarm_dashboard_automation_condition(alias="a"):
    return reelfarm_dashboard_automation_condition_impl(alias)


def reelfarm_expected_automation_condition(alias="a"):
    return reelfarm_expected_automation_condition_impl(alias)


def reelfarm_automation_is_active(automation):
    return reelfarm_automation_is_active_impl(automation)


def active_tiktok_automation_account_ids(conn, account_ids):
    return active_tiktok_automation_account_ids_impl(conn, account_ids, placeholder=db_placeholder())


def mark_missing_reelfarm_automations(conn, product_market_channel_id, seen_reelfarm_ids, synced_at):
    return mark_missing_reelfarm_automations_impl(
        conn,
        product_market_channel_id,
        seen_reelfarm_ids,
        synced_at,
        placeholder=db_placeholder(),
    )


def cleanup_reelfarm_product_from_latest_automations(product_code, automations, synced_at):
    return cleanup_reelfarm_product_from_latest_automations_impl(
        product_code,
        automations,
        synced_at,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def relational_table_counts(conn):
    return relational_table_counts_impl(conn)


def project_products_to_relational(data=None, product_code_filter="", market_code_filter=""):
    return reelfarm_projection_runtime.project_products_to_relational(data, product_code_filter, market_code_filter)


def project_synced_country_to_relational(product, country):
    return reelfarm_projection_runtime.project_synced_country_to_relational(product, country)


def stored_reelfarm_country(product_code, market_code):
    return stored_reelfarm_country_runtime(product_code, market_code)


def enrich_data_with_relational_rollups(data):
    return enrich_data_with_relational_rollups_runtime(data)


def load_external_api_keys():
    return load_external_api_keys_runtime()


def save_external_api_keys(keys):
    save_external_api_keys_runtime(keys)


def create_external_api_key(name, permissions=None):
    return create_external_api_key_runtime(name, permissions)


def revoke_external_api_key(key_id):
    return revoke_external_api_key_runtime(key_id)


def list_external_api_keys():
    return list_external_api_keys_runtime()


def external_api_key_authorized(token, permission):
    return external_api_key_authorized_runtime(token, permission)


def reelfarm_api_key():
    return os.environ.get("REELFARM_API_KEY", "").strip() or load_app_value(REELFARM_API_KEY).strip()


def reelfarm_request(path, query=None):
    return reelfarm_request_impl(
        path,
        query,
        api_key=reelfarm_api_key(),
        base_url=REELFARM_BASE_URL,
        make_ssl_context=make_ssl_context,
    )


def list_payload(payload, key):
    return list_payload_impl(payload, key)


def reelfarm_fetch_automations():
    return reelfarm_fetch_automations_impl(request_fn=reelfarm_request)


def automation_title_product_code_matches(title, product_code):
    return automation_title_product_code_matches_impl(title, product_code)


def reelfarm_product_automation_ids(automations, product_code):
    return reelfarm_product_automation_ids_impl(automations, product_code)


def video_identifier(video):
    return video_identifier_impl(video)


def compact_automation(automation):
    return compact_automation_impl(automation)


def compact_account(account):
    return compact_account_impl(account)


def compact_video(video):
    return compact_video_impl(video)


def collect_zero_play_issue_candidate(candidates, account_id, published_at, view_count, sync_date):
    return collect_zero_play_issue_candidate_impl(candidates, account_id, published_at, view_count, sync_date)


def apply_zero_play_issues(conn, candidates, synced_at):
    return apply_zero_play_issues_impl(
        conn,
        candidates,
        synced_at,
        placeholder=db_placeholder(),
        upsert_row=upsert_row,
        active_tiktok_automation_account_ids=active_tiktok_automation_account_ids,
    )


def cleanup_zero_play_issues_for_non_active_tiktok(conn):
    return cleanup_zero_play_issues_impl(
        conn,
        placeholder=db_placeholder(),
        active_tiktok_automation_account_ids=active_tiktok_automation_account_ids,
    )


def compact_post(post):
    return compact_post_impl(post)


def reelfarm_matches(prefix, automations=None):
    return reelfarm_matches_impl(
        prefix,
        automations=automations,
        fetch_automations_fn=reelfarm_fetch_automations,
        request_fn=reelfarm_request,
    )


def reelfarm_creator_count(result):
    return reelfarm_creator_count_impl(result)


def reelfarm_material_count(result):
    return reelfarm_material_count_impl(result)


def sync_all_reelfarm_records():
    return sync_runtime.sync_all_reelfarm_records()

def sync_all_museon_clone_records():
    return sync_runtime.sync_all_museon_clone_records()

def sync_all_growth_snapshots(days=30):
    return sync_runtime.sync_all_growth_snapshots(days)

def configured_product_codes():
    return configured_product_codes_impl(load_data())


def configured_product_name_map():
    return configured_product_name_map_impl(load_data())


def sync_daily_all_records(days=30):
    return sync_runtime.sync_daily_all_records(days)

def sync_reelfarm_country(prefix, product_id="", country_id="", product_code="", country_code=""):
    return sync_runtime.sync_reelfarm_country(prefix, product_id, country_id, product_code, country_code)


def sync_reelfarm_prefix(prefix, product_id="", country_id="", concept_id="", product_code="", country_code=""):
    return sync_runtime.sync_reelfarm_prefix(prefix, product_id, country_id, concept_id, product_code, country_code)


def cron_authorized(headers):
    return cron_secret_authorized(headers, os.environ.get("CRON_SECRET", "").strip())


def make_auth_token(username):
    return make_auth_token_runtime(username)


def valid_auth_token(token):
    return valid_auth_token_runtime(token)


def database_snapshot():
    return database_snapshot_runtime(relational_table_counts)


def query_value(query, key, default=""):
    return query_value_impl(query, key, default)


def query_limit_offset(query, default=50, max_limit=500):
    return query_limit_offset_impl(query, default, max_limit)


def query_days_window(query):
    return query_days_window_impl(query)


def query_days_snapshot_window(query):
    return query_days_snapshot_window_impl(query)


def post_datetime_bound(value, end=False):
    return post_datetime_bound_impl(value, end, business_material_day_window=business_material_day_window)


def query_filters(query):
    return query_filters_impl(query)


def compact_filters(filters):
    return compact_filters_impl(filters)


def pagination_payload(limit, offset, rows, total=None):
    return pagination_payload_impl(limit, offset, rows, total)


def row_dict(row):
    return row_dict_impl(row)


def common_where(query, date_column="post.published_at", include_post_dates=True):
    return common_where_impl(
        query,
        date_column,
        include_post_dates,
        placeholder=db_placeholder(),
        data_source_channel_code=data_source_channel_code,
        business_material_day_window=business_material_day_window,
    )


def relational_base_from():
    return relational_base_from_impl()


def query_summary(query):
    return query_summary_runtime(query)


def query_country_cards(query):
    return query_country_cards_runtime(query)


def query_countries(query):
    return query_countries_runtime(query)


def query_product_kpis(query):
    return query_product_kpis_runtime(query)


def museon_post_published_at(post):
    return post.get("published_at") or post.get("created_at") or post.get("posted_at") or ""


def query_museon_clone_product_kpis(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    if not product_code:
        raise ValueError("product_code is required.")

    beijing = timezone(timedelta(hours=8))
    current_local = datetime.now(timezone.utc).astimezone(beijing)
    today_start_local = datetime(current_local.year, current_local.month, current_local.day, tzinfo=beijing)
    yesterday_start_local = today_start_local - timedelta(days=1)
    seven_start_local = yesterday_start_local - timedelta(days=6)
    seven_end_local = today_start_local
    yesterday_start_dt = yesterday_start_local.astimezone(timezone.utc)
    yesterday_end_dt = today_start_local.astimezone(timezone.utc)
    seven_start_dt = seven_start_local.astimezone(timezone.utc)
    seven_end_dt = seven_end_local.astimezone(timezone.utc)

    today_creators = set()
    seven_creators = set()
    daily_creator_sets = {
        (seven_start_local + timedelta(days=day_index)).date().isoformat(): set()
        for day_index in range(7)
    }
    today_posts = today_views = today_likes = 0
    seven_posts = seven_views = seven_likes = 0
    seven_comments = seven_shares = seven_bookmarks = 0

    for context in museon_clone_campaigns_for_product(product_code, country_code):
        campaign = context.get("campaign")
        if not campaign:
            continue
        posts = museon_all_posts(campaign.get("id"), seven_start_dt.isoformat(), seven_end_dt.isoformat())
        for post in posts:
            published = parse_iso_datetime(museon_post_published_at(post))
            if not published:
                continue
            account = museon_account_from_post(post)
            account_key = normalize_username(account.get("username")) or str(account.get("id") or "")
            metrics = museon_post_metrics(post)

            if seven_start_dt <= published < seven_end_dt:
                seven_posts += 1
                seven_views += metrics["view_count"]
                seven_likes += metrics["like_count"]
                seven_comments += metrics["comment_count"]
                seven_shares += metrics["share_count"]
                seven_bookmarks += metrics["bookmark_count"]
                if account_key:
                    seven_creators.add(account_key)
                    local_day = published.astimezone(beijing).date().isoformat()
                    if local_day in daily_creator_sets:
                        daily_creator_sets[local_day].add(account_key)

            if yesterday_start_dt <= published < yesterday_end_dt:
                today_posts += 1
                today_views += metrics["view_count"]
                today_likes += metrics["like_count"]
                if account_key:
                    today_creators.add(account_key)

    interactions = seven_likes + seven_comments + seven_shares + seven_bookmarks
    return {
        "product_code": product_code,
        "country_code": country_code or None,
        "source": "museon_clone",
        "today": {
            "creators": len(today_creators),
            "posts": today_posts,
            "views": today_views,
            "likes": today_likes,
            "average_views": round(today_views / today_posts) if today_posts else 0,
            "utc_window": {"start": yesterday_start_dt.isoformat(), "end": yesterday_end_dt.isoformat()},
        },
        "seven_day": {
            "creators": len(seven_creators),
            "posts": seven_posts,
            "views": seven_views,
            "likes": seven_likes,
            "average_creators": sum(len(accounts) for accounts in daily_creator_sets.values()) / 7,
            "average_posts": seven_posts / 7,
            "average_views": round(seven_views / seven_posts) if seven_posts else 0,
            "average_views_per_day": seven_views / 7,
            "average_likes": seven_likes / 7,
            "average_er": (interactions / seven_views * 100) if seven_views else 0,
            "interactions": interactions,
            "utc_window": {"start": seven_start_dt.isoformat(), "end": seven_end_dt.isoformat()},
        },
    }


def query_product_rollups(query):
    return query_product_rollups_runtime(query)


def query_museon_clone_product_rollups(query):
    product_filter = query_value(query, "product_code").upper()
    country_filter = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    products = load_data()
    results = []

    for product in products if isinstance(products, list) else []:
        product_code = product_code_for(product)
        if product_filter and product_code != product_filter:
            continue
        product_row = {
            "product_id": product.get("id"),
            "product_code": product_code,
            "product_name": product.get("name") or product_code,
            "source": "museon_clone",
            "creator_count": 0,
            "material_count": 0,
            "post_count": 0,
            "last_synced_at": "",
            "countries": [],
        }
        for country in product.get("countries") or []:
            country_code = country_code_for(country)
            if country_filter and country_code != country_filter:
                continue
            campaign = museon_clone_campaign(product_code, country_code)
            account_ids = set()
            post_count = 0
            latest = ""
            if campaign:
                posts = museon_all_posts(campaign.get("id"))
                for post in posts:
                    post_count += 1
                    account = museon_account_from_post(post)
                    account_key = normalize_username(account.get("username")) or str(account.get("id") or "")
                    if account_key:
                        account_ids.add(account_key)
                    published_at = museon_post_published_at(post)
                    if published_at and published_at > latest:
                        latest = published_at
            country_row = {
                "country_id": country.get("id"),
                "country_code": country_code,
                "country_name": country.get("name") or country_code,
                "creator_count": len(account_ids),
                "material_count": post_count,
                "post_count": post_count,
                "last_synced_at": latest,
                "campaign_id": campaign.get("id") if campaign else None,
                "campaign_name": (campaign.get("name") or campaign.get("title")) if campaign else None,
            }
            product_row["countries"].append(country_row)
            product_row["creator_count"] += country_row["creator_count"]
            product_row["material_count"] += country_row["material_count"]
            product_row["post_count"] += country_row["post_count"]
            if latest and latest > product_row["last_synced_at"]:
                product_row["last_synced_at"] = latest
        results.append(product_row)
    return results


def product_channel_views_for_window(product_code, channel_code, utc_start, utc_end):
    return growth_runtime.product_channel_views_for_window(product_code, channel_code, utc_start, utc_end)


def product_channel_daily_views(product_code, channel_code, utc_start, utc_end):
    return growth_runtime.product_channel_daily_views(product_code, channel_code, utc_start, utc_end)


def product_business_material_daily_stats(product_code, utc_start, utc_end):
    return growth_runtime.product_business_material_daily_stats(product_code, utc_start, utc_end)


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



def _account_alert_display_name(item):
    return account_alert_display_name_impl(item)


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

def product_active_reelfarm_expected_schedule_count(product_code):
    return growth_runtime.product_active_reelfarm_expected_schedule_count(product_code)


def product_active_reelfarm_expected_automation_count(product_code):
    return growth_runtime.product_active_reelfarm_expected_automation_count(product_code)


def latest_snapshot_views_by_source(product_code, snapshot_date):
    return growth_runtime.latest_snapshot_views_by_source(product_code, snapshot_date)


def product_business_growth_daily_stats(product_code, windows):
    return growth_runtime.product_business_growth_daily_stats(product_code, windows)


def mixpanel_event_daily_counts(config, event_name, utc_start, utc_end, value_type="general"):
    return growth_runtime.mixpanel_event_daily_counts(config, event_name, utc_start, utc_end, value_type)


def mixpanel_event_business_material_counts(config, event_name, utc_start, utc_end, value_type="general", date_mapper=None):
    return mixpanel_event_business_material_counts_impl(
        config,
        event_name,
        utc_start,
        utc_end,
        value_type,
        date_mapper,
        default_region=MIXPANEL_REGION,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        business_material_date_for_utc_datetime=business_material_date_for_utc_datetime,
        make_ssl_context=make_ssl_context,
    )


def mixpanel_event_user_unique_query_count(config, event_name, utc_start, utc_end):
    return growth_runtime.mixpanel_event_user_unique_query_count(config, event_name, utc_start, utc_end)


def mixpanel_event_total(config, event_name, utc_start, utc_end, value_type="general"):
    return growth_runtime.mixpanel_event_total(config, event_name, utc_start, utc_end, value_type)


def sync_product_growth_snapshot(product_code, report_date=""):
    return growth_runtime.sync_product_growth_snapshot(product_code, report_date)


def sync_product_growth_snapshots(product_code, days=30):
    return growth_runtime.sync_product_growth_snapshots(product_code, days)


def growth_dashboard_payload(query):
    return growth_runtime.growth_dashboard_payload(query)

def business_material_report_payload(query):
    return growth_runtime.business_material_report_payload(query)

def clean_tag(value):
    return clean_tag_impl(value)


def existing_tag_value(conn, table, scope_column, scope_value, tag):
    return existing_tag_value_impl(
        conn,
        table,
        scope_column,
        scope_value,
        tag,
        placeholder=db_placeholder(),
    )


def account_tags_payload(account_ids):
    return account_tags_payload_impl(
        account_ids,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def account_issues_payload(account_ids):
    return account_issues_payload_impl(
        account_ids,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
        active_tiktok_automation_account_ids=active_tiktok_automation_account_ids,
    )


def add_account_issue(account_id, issue):
    return add_account_issue_impl(
        account_id,
        issue,
        clean_issue=clean_tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        upsert_row=upsert_row,
    )


def delete_account_issue(account_id, issue):
    return delete_account_issue_impl(
        account_id,
        issue,
        clean_issue=clean_tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def attach_account_issues(rows):
    return attach_account_issues_impl(rows, account_issues_payload)


def product_tags_payload(product_code):
    return product_tags_payload_impl(
        product_code,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def create_product_tag(product_code, tag):
    return create_product_tag_impl(
        product_code,
        tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        upsert_row=upsert_row,
        placeholder=db_placeholder(),
    )


def delete_product_tag(product_code, tag, remove_assignments=True):
    return delete_product_tag_impl(
        product_code,
        tag,
        remove_assignments=remove_assignments,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def add_account_tag(account_id, tag):
    return add_account_tag_impl(
        account_id,
        tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        upsert_row=upsert_row,
        placeholder=db_placeholder(),
    )


def delete_account_tag(account_id, tag):
    return delete_account_tag_impl(
        account_id,
        tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def museon_request(path, params=None):
    return museon_runtime.request(path, params)


def museon_campaigns(force=False):
    return museon_runtime.campaigns(force)


def museon_clone_campaign(product_code, country_code):
    return museon_runtime.clone_campaign(product_code, country_code)


def museon_clone_campaigns_for_product(product_code, country_code=""):
    return museon_runtime.clone_campaigns_for_product(product_code, country_code)


def museon_posts(campaign_id, date_from="", date_to="", username="", page=1, page_size=100, sort=""):
    return museon_runtime.posts(campaign_id, date_from, date_to, username, page, page_size, sort)


def museon_all_posts(campaign_id, date_from="", date_to="", max_pages=40):
    return museon_runtime.all_posts(campaign_id, date_from, date_to, max_pages)


def local_product_country_context(product_code, country_code):
    return museon_runtime.local_product_country_context(product_code, country_code)


def reelfarm_account_lookup(product_code, country_code):
    return museon_runtime.reelfarm_account_lookup(product_code, country_code, query_reelfarm_accounts)


def museon_content_download_images(content_id):
    return museon_runtime.content_download_images(content_id)


def hydrate_museon_images_for_rows(conn, row_data_list):
    return museon_runtime.hydrate_images_for_rows(conn, row_data_list)


def local_product_country_record(product_id="", country_id="", product_code="", country_code=""):
    return museon_runtime.local_product_country_record(product_id, country_id, product_code, country_code)


def sync_museon_clone_country(product_id="", country_id="", product_code="", country_code=""):
    return museon_runtime.sync_clone_country(product_id, country_id, product_code, country_code)


def query_museon_clone_accounts(query):
    return museon_runtime.query_clone_accounts(query, attach_account_issues_fn=attach_account_issues)


def reelfarm_detailed_rows_for_username(product_code, country_code, username):
    return museon_runtime.reelfarm_detailed_rows_for_username(product_code, country_code, username)


def nearest_reelfarm_row(museon_post, rf_rows):
    return museon_runtime.nearest_reelfarm_row(museon_post, rf_rows)


def museon_post_to_detailed_row(post, product, country, rf_match=None):
    return museon_runtime.post_to_detailed_row(post, product, country, rf_match)


def query_museon_clone_account_posts(query):
    return museon_runtime.query_clone_account_posts(query)


def query_reelfarm_accounts(query):
    return query_accounts_runtime(query)


def query_accounts(query):
    return query_reelfarm_accounts(query)


def daily_feishu_service():
    return daily_feishu_runtime.daily_feishu_service()


def send_feishu_message(message):
    return daily_feishu_service().send_feishu_message(message)


def daily_feishu_report_payload(report_date=""):
    return daily_feishu_service().report_payload(report_date)


def daily_feishu_report_card_data(report_date="", report=None):
    return daily_feishu_service().report_card_data(report_date, report)


def daily_feishu_report_card(report_date="", report=None):
    return daily_feishu_service().report_card(report_date, report)


def send_daily_feishu_report(report_date="", require_synced=False, mode="template"):
    return daily_feishu_service().send_report(report_date, require_synced=require_synced, mode=mode)


def detailed_select():
    return detailed_select_impl()


def detailed_row(row):
    return detailed_row_impl(row)


def query_posts(query, top_metric=""):
    return query_posts_runtime(query, top_metric)


def query_materials(query):
    return query_materials_runtime(query)


def query_daily_metrics(query):
    return query_daily_metrics_runtime(query)


def data_query_payload(query):
    return data_query_payload_runtime(query)


def ai_materials_payload(query):
    return ai_materials_payload_runtime(query)
