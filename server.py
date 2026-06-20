#!/usr/bin/env python3
import json
import os
import re
import socket
import sys
import time
import webbrowser
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
from server_modules.services.publish_check_service import (
    beijing_day_window as beijing_day_window_impl,
    publish_check_reminder_text as publish_check_reminder_text_impl,
)
from server_modules.services.publish_check_runtime import (
    product_country_lookup as publish_check_product_country_lookup_runtime,
    publish_check_accounts as publish_check_accounts_runtime,
    run as run_publish_check_runtime,
    send_reminder as send_publish_check_reminder_runtime,
)
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
    PUBLISH_CHECK_STATE_KEY,
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
    load_publish_check_state,
    make_auth_token as make_auth_token_runtime,
    make_ssl_context,
    reset_schema_init_cache,
    save_app_value,
    save_data,
    save_publish_check_state,
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
from server_modules.services import daily_feishu_runtime, sync_runtime
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
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1").strip().rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4.1-mini").strip()
FALLBACK_LLM_MODELS = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
]


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
    data = data if isinstance(data, list) else load_data()
    now = datetime.now(timezone.utc).isoformat()
    channel_id = stable_id("channel", "TIKTOK")
    product_code_filter = str(product_code_filter or "").strip().upper()
    market_code_filter = str(market_code_filter or "").strip().upper()

    with connect_db() as conn:
        init_relational_schema(conn)
        zero_play_candidates = {}
        upsert_row(
            conn,
            "channels",
            {"id": channel_id, "name": "TikTok", "code": "TIKTOK"},
            ["code"],
        )

        for product in data:
            if not isinstance(product, dict):
                continue

            product_id = str(product.get("id") or stable_id("product", product.get("name")))
            product_code = product_code_for(product)
            if product_code_filter and product_code != product_code_filter:
                continue

            upsert_row(
                conn,
                "products",
                {
                    "id": product_id,
                    "name": str(product.get("name") or "Untitled Product"),
                    "code": product_code,
                    "owner_type": product.get("folder") or product.get("owner_type"),
                    "logo_url": product.get("logo") or "",
                    "created_at": product.get("created_at") or now,
                    "updated_at": now,
                },
                ["id"],
            )

            for country in product.get("countries", []) or []:
                if not isinstance(country, dict):
                    continue

                market_code = country_code_for(country)
                if market_code_filter and market_code != market_code_filter:
                    continue

                market_id = stable_id("market", market_code)
                product_market_id = stable_id("product_market", product_id, market_id)
                product_market_channel_id = stable_id("product_market_channel", product_market_id, channel_id)

                upsert_row(
                    conn,
                    "markets",
                    {"id": market_id, "name": str(country.get("name") or market_code), "code": market_code},
                    ["code"],
                )
                upsert_row(
                    conn,
                    "product_markets",
                    {"id": product_market_id, "product_id": product_id, "market_id": market_id},
                    ["product_id", "market_id"],
                )
                upsert_row(
                    conn,
                    "product_market_channels",
                    {
                        "id": product_market_channel_id,
                        "product_market_id": product_market_id,
                        "channel_id": channel_id,
                    },
                    ["product_market_id", "channel_id"],
                )

                for concept in country.get("concepts", []) or []:
                    if not isinstance(concept, dict):
                        continue
                    concept_name = str(concept.get("group") or "默认 Topic").strip() or "默认 Topic"
                    format_name = str(concept.get("name") or "默认 Format").strip() or "默认 Format"
                    concept_id = stable_id("concept", product_id, concept_name)
                    format_id = stable_id("format", concept_id, format_name)
                    upsert_row(
                        conn,
                        "concepts",
                        {"id": concept_id, "product_id": product_id, "name": concept_name, "description": ""},
                        ["product_id", "name"],
                    )
                    upsert_row(
                        conn,
                        "formats",
                        {"id": format_id, "concept_id": concept_id, "name": format_name, "description": ""},
                        ["concept_id", "name"],
                    )

                reel_farm_result = country.get("reelFarmResult")
                has_reelfarm_result = isinstance(reel_farm_result, dict)
                result = reel_farm_result if has_reelfarm_result else {}
                synced_at = country.get("reelFarmSyncedAt") or now
                seen_reelfarm_automation_ids = set()
                for card in result.get("cards", []) or []:
                    if not isinstance(card, dict):
                        continue

                    account = card.get("account") if isinstance(card.get("account"), dict) else {}
                    automation = card.get("automation") if isinstance(card.get("automation"), dict) else {}
                    automation_reelfarm_id = str(
                        automation.get("automation_id") or stable_id("automation_source", automation.get("title"))
                    )
                    automation_title = str(automation.get("title") or automation_reelfarm_id)
                    reelfarm_account_id = str(
                        account.get("tiktok_account_id")
                        or automation.get("tiktok_account_id")
                        or account.get("account_username")
                        or automation_reelfarm_id
                    )
                    account_id = stable_id("account", product_market_channel_id, reelfarm_account_id)
                    automation_id = stable_id("automation", automation_reelfarm_id)
                    seen_reelfarm_automation_ids.add(automation_reelfarm_id)
                    is_active_tiktok_automation = reelfarm_automation_is_active(automation)
                    if is_active_tiktok_automation:
                        zero_play_candidates.setdefault(account_id, [])

                    upsert_row(
                        conn,
                        "accounts",
                        {
                            "id": account_id,
                            "product_market_channel_id": product_market_channel_id,
                            "source": "reelfarm",
                            "source_account_id": reelfarm_account_id,
                            "reelfarm_account_id": reelfarm_account_id,
                            "username": account.get("account_username") or account.get("account_name") or "",
                            "display_name": account.get("account_name") or "",
                            "avatar_url": account.get("account_image") or "",
                            "status": account.get("status") or automation.get("status") or "",
                        },
                        ["product_market_channel_id", "reelfarm_account_id"],
                    )
                    upsert_row(
                        conn,
                        "automations",
                        {
                            "id": automation_id,
                            "product_market_channel_id": product_market_channel_id,
                            "account_id": account_id,
                            "source": "reelfarm",
                            "source_automation_id": automation_reelfarm_id,
                            "reelfarm_automation_id": automation_reelfarm_id,
                            "name": automation_title,
                            "status": automation.get("status") or "",
                            "schedule": db_json(automation.get("schedule", [])),
                            "settings_json": db_json(automation),
                            "post_mode": automation.get("post_mode") or reelfarm_post_mode(automation),
                            "publish_method": automation.get("publish_method") or reelfarm_publish_method(automation),
                            "sync_status": "present",
                            "last_seen_at": synced_at,
                            "deleted_at": "",
                            "created_at": automation.get("created_at") or "",
                            "synced_at": synced_at,
                        },
                        ["reelfarm_automation_id"],
                    )

                    concept_name, format_name = parse_concept_format_from_automation(
                        automation_title,
                        market_code,
                        product_code,
                    )
                    concept_id = None
                    format_id = None
                    if concept_name and format_name:
                        concept_id = stable_id("concept", product_id, concept_name)
                        format_id = stable_id("format", concept_id, format_name)
                        upsert_row(
                            conn,
                            "concepts",
                            {"id": concept_id, "product_id": product_id, "name": concept_name, "description": ""},
                            ["product_id", "name"],
                        )
                        upsert_row(
                            conn,
                            "formats",
                            {"id": format_id, "concept_id": concept_id, "name": format_name, "description": ""},
                            ["concept_id", "name"],
                        )

                    posts_by_video = {
                        str(post.get("video_id")): post
                        for post in (card.get("posts") or [])
                        if isinstance(post, dict)
                    }
                    for video in card.get("videos", []) or []:
                        if not isinstance(video, dict):
                            continue
                        reelfarm_video_id = str(video.get("video_id") or video.get("id") or "")
                        if not reelfarm_video_id:
                            continue
                        material_id = stable_id("material", reelfarm_video_id)
                        images = video.get("slideshow_images") if isinstance(video.get("slideshow_images"), list) else []
                        upsert_row(
                            conn,
                            "materials",
                            {
                                "id": material_id,
                                "automation_id": automation_id,
                                "product_market_channel_id": product_market_channel_id,
                                "account_id": account_id,
                                "concept_id": concept_id,
                                "format_id": format_id,
                                "source": "reelfarm",
                                "source_material_id": reelfarm_video_id,
                                "reelfarm_video_id": reelfarm_video_id,
                                "video_type": video.get("video_type") or "",
                                "hook": video.get("hook") or "",
                                "prompt": video.get("prompt") or "",
                                "images_json": db_json(images),
                                "slide_count": int_or_none(video.get("slide_count")) or len(images),
                                "status": video.get("status") or "",
                                "created_at": video.get("created_at") or "",
                                "finished_at": video.get("finished_at") or "",
                                "synced_at": synced_at,
                            },
                            ["reelfarm_video_id"],
                        )

                        post = posts_by_video.get(reelfarm_video_id)
                        if not isinstance(post, dict):
                            continue
                        reelfarm_post_id = str(post.get("post_id") or stable_id("post_source", material_id))
                        post_id = stable_id("post", reelfarm_post_id)
                        snapshot_date = utc_snapshot_date()
                        if is_active_tiktok_automation:
                            collect_zero_play_issue_candidate(
                                zero_play_candidates,
                                account_id,
                                post.get("published_at"),
                                post.get("view_count"),
                                business_date_string(synced_at),
                            )
                        upsert_row(
                            conn,
                            "posts",
                            {
                                "id": post_id,
                                "material_id": material_id,
                                "account_id": account_id,
                                "source": "reelfarm",
                                "source_post_id": reelfarm_post_id,
                                "reelfarm_post_id": reelfarm_post_id,
                                "status": post.get("status") or "",
                                "title": post.get("title") or "",
                                "published_at": post.get("published_at") or "",
                                "published_at_readable": post.get("published_at_readable") or "",
                                "view_count": int_or_none(post.get("view_count")),
                                "like_count": int_or_none(post.get("like_count")),
                                "comment_count": int_or_none(post.get("comment_count")),
                                "share_count": int_or_none(post.get("share_count")),
                                "bookmark_count": int_or_none(post.get("bookmark_count")),
                                "synced_at": synced_at,
                            },
                            ["reelfarm_post_id"],
                        )
                        upsert_row(
                            conn,
                            "post_daily_snapshots",
                            {
                                "id": stable_id("post_daily_snapshot", post_id, snapshot_date),
                                "post_id": post_id,
                                "snapshot_date": snapshot_date,
                                "view_count": int_or_none(post.get("view_count")),
                                "like_count": int_or_none(post.get("like_count")),
                                "comment_count": int_or_none(post.get("comment_count")),
                                "share_count": int_or_none(post.get("share_count")),
                                "bookmark_count": int_or_none(post.get("bookmark_count")),
                                "synced_at": synced_at,
                            },
                            ["post_id", "snapshot_date"],
                        )

                if has_reelfarm_result:
                    mark_missing_reelfarm_automations(
                        conn,
                        product_market_channel_id,
                        seen_reelfarm_automation_ids,
                        synced_at,
                    )

        apply_zero_play_issues(conn, zero_play_candidates, now)
        counts = relational_table_counts(conn)
        conn.commit()

    return {
        "ok": True,
        "projected_at": now,
        "database_backend": "postgres" if using_postgres() else "sqlite",
        "filters": {
            "product_code": product_code_filter or None,
            "market_code": market_code_filter or None,
        },
        "tables": counts,
    }


def project_synced_country_to_relational(product, country):
    if not isinstance(product, dict) or not isinstance(country, dict):
        return None

    scoped_product = dict(product)
    scoped_country = dict(country)
    scoped_product["countries"] = [scoped_country]
    product_code = product_code_for(scoped_product)
    market_code = country_code_for(scoped_country)
    return project_products_to_relational(
        data=[scoped_product],
        product_code_filter=product_code,
        market_code_filter=market_code,
    )


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
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"""
            SELECT
                COUNT(DISTINCT post.id) AS posts,
                COUNT(DISTINCT acc.id) AS creators,
                COALESCE(SUM(post.view_count), 0) AS views,
                COALESCE(SUM(post.like_count), 0) AS likes
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}
              AND post.published_at >= {placeholder}
              AND post.published_at < {placeholder}
              AND post.id IS NOT NULL
            """,
            (channel_code, str(product_code or "").upper(), utc_start.isoformat(), utc_end.isoformat()),
        ).fetchone()
    data = row_dict(row)
    return {
        "posts": int(data.get("posts") or 0),
        "creators": int(data.get("creators") or 0),
        "views": int(data.get("views") or 0),
        "likes": int(data.get("likes") or 0),
    }


def product_channel_daily_views(product_code, channel_code, utc_start, utc_end):
    placeholder = db_placeholder()
    daily = {}
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                post.id AS post_id,
                post.published_at AS published_at,
                COALESCE(post.view_count, 0) AS view_count
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}
              AND post.published_at >= {placeholder}
              AND post.published_at < {placeholder}
              AND post.id IS NOT NULL
            GROUP BY post.id, post.published_at, post.view_count
            """,
            (channel_code, str(product_code or "").upper(), utc_start.isoformat(), utc_end.isoformat()),
        ).fetchall()
    for row in rows:
        item = row_dict(row)
        published_at = parse_iso_datetime(item.get("published_at"))
        report_date = report_date_for_utc_datetime(published_at)
        if not report_date:
            continue
        daily[report_date] = daily.get(report_date, 0) + int(item.get("view_count") or 0)
    return daily


def product_business_material_daily_stats(product_code, utc_start, utc_end):
    placeholder = db_placeholder()
    daily = {}
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                ch.code AS channel_code,
                a.id AS automation_id,
                acc.id AS account_id,
                post.id AS post_id,
                mat.id AS material_id,
                mat.created_at AS material_created_at,
                post.published_at AS published_at,
                COALESCE(post.view_count, 0) AS view_count
            {relational_base_from()}
            WHERE p.code = {placeholder}
              AND ch.code IN ('TIKTOK', 'MUSEON_CLONE')
              AND (
                (
                  ch.code = 'TIKTOK'
                  AND LOWER(COALESCE(a.status, '')) = 'active'
                  AND mat.id IS NOT NULL
                  AND post.id IS NOT NULL
                  AND mat.created_at >= {placeholder}
                  AND mat.created_at < {placeholder}
                )
                OR (
                  ch.code = 'MUSEON_CLONE'
                  AND post.id IS NOT NULL
                  AND post.published_at >= {placeholder}
                  AND post.published_at < {placeholder}
                )
              )
            GROUP BY ch.code, a.id, acc.id, post.id, mat.id, mat.created_at, post.published_at, post.view_count
            """,
            (
                str(product_code or "").upper(),
                utc_start.isoformat(),
                utc_end.isoformat(),
                utc_start.isoformat(),
                utc_end.isoformat(),
            ),
        ).fetchall()
    for row in rows:
        item = row_dict(row)
        source_key = "clone" if item.get("channel_code") == "MUSEON_CLONE" else "reelfarm"
        source_at = item.get("published_at") if source_key == "clone" else item.get("material_created_at")
        report_date = business_material_date_for_utc_datetime(parse_iso_datetime(source_at))
        if not report_date:
            continue
        entry = daily.setdefault(report_date, {
            "reelfarm_materials": set(),
            "clone_materials": set(),
            "reelfarm_posted_materials": set(),
            "reelfarm_published_automations": set(),
            "clone_posts": set(),
            "reelfarm_views": 0,
            "clone_views": 0,
        })
        material_id = item.get("material_id") or item.get("post_id")
        if source_key == "clone":
            if material_id:
                entry["clone_materials"].add(str(material_id))
            if item.get("post_id"):
                entry["clone_posts"].add(str(item.get("post_id")))
            entry["clone_views"] += int(item.get("view_count") or 0)
        else:
            if material_id:
                entry["reelfarm_materials"].add(str(material_id))
            if item.get("post_id"):
                if material_id:
                    entry["reelfarm_posted_materials"].add(str(material_id))
                published_identity = item.get("account_id") or item.get("automation_id")
                if published_identity:
                    entry["reelfarm_published_automations"].add(str(published_identity))
                entry["reelfarm_views"] += int(item.get("view_count") or 0)
    normalized = {}
    for report_date, item in daily.items():
        reelfarm_materials = len(item.get("reelfarm_materials") or set())
        clone_materials = len(item.get("clone_materials") or set())
        reelfarm_posts = len(item.get("reelfarm_posted_materials") or set())
        reelfarm_published_automations = len(item.get("reelfarm_published_automations") or set())
        clone_posts = len(item.get("clone_posts") or set())
        reelfarm_views = int(item.get("reelfarm_views") or 0)
        clone_views = int(item.get("clone_views") or 0)
        normalized[report_date] = {
            "reelfarm_materials": reelfarm_materials,
            "clone_materials": clone_materials,
            "total_materials": reelfarm_materials + clone_materials,
            "reelfarm_posts": reelfarm_posts,
            "reelfarm_published_automations": reelfarm_published_automations,
            "clone_posts": clone_posts,
            "total_posts": reelfarm_posts + clone_posts,
            "reelfarm_views": reelfarm_views,
            "clone_views": clone_views,
            "total_views": reelfarm_views + clone_views,
            "reelfarm_avg_views": (reelfarm_views / reelfarm_posts) if reelfarm_posts else None,
            "clone_avg_views": (clone_views / clone_posts) if clone_posts else None,
        }
    return normalized


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
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT DISTINCT a.id, a.schedule
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            JOIN automations a ON a.product_market_channel_id = pmc.id
            WHERE p.code = {placeholder}
              AND ch.code = 'TIKTOK'
              AND {reelfarm_expected_automation_condition("a")}
            """,
            (str(product_code or "").upper(),),
        ).fetchall()

    return sum(reelfarm_schedule_slot_count(row_dict(row).get("schedule")) for row in rows)


def product_active_reelfarm_expected_automation_count(product_code):
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"""
            SELECT COUNT(DISTINCT acc.id) AS automation_count
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            JOIN automations a ON a.product_market_channel_id = pmc.id
            JOIN accounts acc ON acc.id = a.account_id
            WHERE p.code = {placeholder}
              AND ch.code = 'TIKTOK'
              AND {reelfarm_expected_automation_condition("a")}
            """,
            (str(product_code or "").upper(),),
        ).fetchone()
    return int(row_dict(row).get("automation_count") or 0)


def latest_snapshot_views_by_source(product_code, snapshot_date):
    product_code = str(product_code or "").upper()
    snapshot_date = str(snapshot_date or "")[:10]
    if not product_code or not snapshot_date:
        return {}
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                ch.code AS channel_code,
                post.id AS post_id,
                COALESCE((
                    SELECT snap.view_count
                    FROM post_daily_snapshots snap
                    WHERE snap.post_id = post.id
                      AND snap.snapshot_date <= {placeholder}
                    ORDER BY snap.snapshot_date DESC
                    LIMIT 1
                ), 0) AS view_count
            {relational_base_from()}
            WHERE p.code = {placeholder}
              AND ch.code IN ('TIKTOK', 'MUSEON_CLONE')
              AND post.id IS NOT NULL
            GROUP BY ch.code, post.id
            """,
            (snapshot_date, product_code),
        ).fetchall()
    snapshots = {}
    for row in rows:
        item = row_dict(row)
        source = "clone" if item.get("channel_code") == "MUSEON_CLONE" else "reelfarm"
        post_id = str(item.get("post_id") or "")
        if post_id:
            snapshots.setdefault(source, {})[post_id] = int(item.get("view_count") or 0)
    return snapshots


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
    daily = {}
    for window in windows:
        report_date = str(window["report_date"])
        previous_date = (datetime.strptime(report_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
        current = snapshot_cache.get(report_date, {})
        previous = snapshot_cache.get(previous_date, {})
        entry = {
            "reelfarm_posts": 0,
            "clone_posts": 0,
            "reelfarm_views": 0,
            "clone_views": 0,
        }
        for source, view_key, post_key in (
            ("reelfarm", "reelfarm_views", "reelfarm_posts"),
            ("clone", "clone_views", "clone_posts"),
        ):
            current_posts = current.get(source, {})
            previous_posts = previous.get(source, {})
            for post_id, current_views in current_posts.items():
                previous_views = int(previous_posts.get(post_id) or 0)
                delta = int(current_views or 0) - previous_views
                if delta < 0:
                    delta = 0
                if delta > 0:
                    entry[post_key] += 1
                    entry[view_key] += delta
        entry["total_posts"] = entry["reelfarm_posts"] + entry["clone_posts"]
        entry["total_views"] = entry["reelfarm_views"] + entry["clone_views"]
        daily[report_date] = entry
    return daily


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
    onboarding_unique = mixpanel_event_total(mixpanel_config, onboarding_event, window["utc_start"], window["utc_end"], "unique")
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
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(conn, "product_daily_growth_snapshots", record, ["product_code", "report_date"])
        conn.commit()
    return record


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
    onboarding_daily = mixpanel_event_daily_counts(mixpanel_config, onboarding_event, overall_utc_start, overall_utc_end, "unique")
    now = datetime.now(timezone.utc).isoformat()
    records = []
    with connect_db() as conn:
        init_relational_schema(conn)
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
            upsert_row(conn, "product_daily_growth_snapshots", record, ["product_code", "report_date"])
            records.append(record)
        conn.commit()
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
        product_mixpanel_config=product_mixpanel_config,
        product_mixpanel_event_name=product_mixpanel_event_name,
        mixpanel_event_user_unique_query_count=mixpanel_event_user_unique_query_count,
        normalize_business_report_row=normalize_business_report_row,
        summarize_business_report_rows=summarize_business_report_rows,
        report_timezone_name=REPORT_TIMEZONE_NAME,
        mixpanel_timezone_name=MIXPANEL_TIMEZONE_NAME,
    )

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
    return museon_request_impl(
        path,
        params,
        api_key=MUSEON_API_KEY,
        base_url=MUSEON_BASE_URL,
        user_agent=MUSEON_USER_AGENT,
        make_ssl_context=make_ssl_context,
    )


def museon_campaigns(force=False):
    return museon_campaigns_impl(
        request_fn=museon_request,
        workspace_id=MUSEON_WORKSPACE_ID,
        force=force,
    )


def museon_clone_campaign(product_code, country_code):
    return museon_clone_campaign_impl(
        product_code,
        country_code,
        campaigns_fn=museon_campaigns,
    )


def museon_clone_campaigns_for_product(product_code, country_code=""):
    return museon_clone_campaigns_for_product_impl(
        product_code,
        country_code,
        products=load_data(),
        country_codes=COUNTRY_CODES,
        code_from_name=code_from_name,
        clone_campaign_fn=museon_clone_campaign,
    )


def museon_posts(campaign_id, date_from="", date_to="", username="", page=1, page_size=100, sort=""):
    return museon_posts_impl(
        campaign_id,
        date_from,
        date_to,
        username,
        page,
        page_size,
        sort,
        request_fn=museon_request,
        post_datetime_bound=post_datetime_bound,
    )


def museon_all_posts(campaign_id, date_from="", date_to="", max_pages=40):
    return museon_all_posts_impl(
        campaign_id,
        date_from,
        date_to,
        max_pages,
        posts_fn=museon_posts,
    )


def local_product_country_context(product_code, country_code):
    products = load_data()
    product_context = {"id": None, "code": product_code, "name": product_code}
    country_context = {"id": None, "code": country_code, "name": country_code}
    for product in products if isinstance(products, list) else []:
        code = product_code_for(product)
        if code != product_code:
            continue
        product_context = {"id": product.get("id"), "code": code, "name": product.get("name") or product_code}
        for country in product.get("countries") or []:
            ccode = country_code_for(country)
            if ccode == country_code:
                country_context = {"id": country.get("id"), "code": ccode, "name": country.get("name") or country_code}
                break
        break
    return product_context, country_context


def reelfarm_account_lookup(product_code, country_code):
    lookup = {}
    query = {"product_code": [product_code], "country_code": [country_code]}
    for row in query_reelfarm_accounts(query):
        username = normalize_username(row.get("username") or row.get("display_name"))
        if username:
            lookup[username] = row
    return lookup


def museon_content_download_images(content_id):
    return museon_content_download_images_impl(content_id, request_fn=museon_request)


def hydrate_museon_images_for_rows(conn, row_data_list):
    placeholder = db_placeholder()
    hydrated = []
    changed = False
    for data in row_data_list:
        item = dict(data)
        existing_images = parse_json_list(item.get("images_json"))
        if existing_images:
            hydrated.append(item)
            continue

        content_id = museon_content_id_from_material_source(item.get("reelfarm_video_id"))
        images = museon_content_download_images(content_id)
        if images:
            images_json = db_json(images)
            slide_count = int_or_none(item.get("slide_count")) or len(images)
            item["images_json"] = images_json
            item["slide_count"] = slide_count
            conn.execute(
                f"""
                UPDATE materials
                SET images_json = {placeholder},
                    slide_count = CASE
                        WHEN slide_count IS NULL OR slide_count = 0 THEN {placeholder}
                        ELSE slide_count
                    END
                WHERE id = {placeholder}
                """,
                (images_json, slide_count, item.get("material_id")),
            )
            changed = True
        hydrated.append(item)

    if changed:
        conn.commit()
    return hydrated


def local_product_country_record(product_id="", country_id="", product_code="", country_code=""):
    product_code = str(product_code or "").strip().upper()
    country_code = str(country_code or "").strip().upper()
    for product in load_data():
        if not isinstance(product, dict):
            continue
        pcode = product_code_for(product)
        if product_id and str(product.get("id") or "") != str(product_id):
            continue
        if product_code and pcode != product_code:
            continue
        for country in product.get("countries") or []:
            if not isinstance(country, dict):
                continue
            ccode = country_code_for(country)
            if country_id and str(country.get("id") or "") != str(country_id):
                continue
            if country_code and ccode != country_code:
                continue
            return product, country, pcode, ccode
    return (
        {
            "id": product_id or stable_id("product", product_code),
            "name": product_code or "Product",
            "reelFarmCode": product_code,
            "folder": "",
            "logo": "",
        },
        {
            "id": country_id or stable_id("country", country_code),
            "name": country_code or "Country",
            "reelFarmCode": country_code,
        },
        product_code,
        country_code,
    )


def sync_museon_clone_country(product_id="", country_id="", product_code="", country_code=""):
    product, country, product_code, country_code = local_product_country_record(product_id, country_id, product_code, country_code)
    if not product_code or not country_code:
        raise ValueError("Missing product_code or country_code.")

    started = time.perf_counter()
    synced_at = datetime.now(timezone.utc).isoformat()
    campaign = museon_clone_campaign(product_code, country_code)
    if not campaign:
        return {
            "ok": True,
            "skipped": True,
            "source": "museon_clone",
            "product_code": product_code,
            "country_code": country_code,
            "creator_count": 0,
            "material_count": 0,
            "post_count": 0,
            "synced_at": synced_at,
            "message": f"No Museon clone campaign found for {country_code}-{product_code}.",
        }

    posts = museon_all_posts(campaign.get("id"), max_pages=0)
    channel_id = stable_id("channel", "MUSEON_CLONE")
    product_row_id = str(product.get("id") or stable_id("product", product_code))
    market_id = stable_id("market", country_code)
    product_market_id = stable_id("product_market", product_row_id, market_id)
    product_market_channel_id = stable_id("product_market_channel", product_market_id, channel_id)
    campaign_name = str(campaign.get("name") or campaign.get("title") or f"{country_code}-{product_code}-Clone")
    campaign_id = str(campaign.get("id") or stable_id("museon_campaign", campaign_name))
    account_ids = set()
    material_count = 0
    post_count = 0

    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(conn, "channels", {"id": channel_id, "name": "Clone Slide Show", "code": "MUSEON_CLONE"}, ["code"])
        upsert_row(
            conn,
            "products",
            {
                "id": product_row_id,
                "name": str(product.get("name") or product_code),
                "code": product_code,
                "owner_type": product.get("folder") or product.get("owner_type") or "",
                "logo_url": product.get("logo") or product.get("logo_url") or "",
                "created_at": product.get("created_at") or synced_at,
                "updated_at": synced_at,
            },
            ["id"],
        )
        upsert_row(conn, "markets", {"id": market_id, "name": str(country.get("name") or country_code), "code": country_code}, ["code"])
        upsert_row(conn, "product_markets", {"id": product_market_id, "product_id": product_row_id, "market_id": market_id}, ["product_id", "market_id"])
        upsert_row(
            conn,
            "product_market_channels",
            {"id": product_market_channel_id, "product_market_id": product_market_id, "channel_id": channel_id},
            ["product_market_id", "channel_id"],
        )

        for post in posts:
            if not isinstance(post, dict):
                continue
            account = museon_account_from_post(post)
            username = normalize_username(account.get("username")) or normalize_username(account.get("display_name"))
            if not username:
                continue
            museon_account_id = str(account.get("id") or username)
            account_source_id = f"museon:{museon_account_id}"
            account_id = stable_id("museon_account", product_market_channel_id, account_source_id)
            automation_source_id = f"museon:{campaign_id}:{museon_account_id}"
            automation_id = stable_id("museon_automation", automation_source_id)
            post_source_id = str(post.get("id") or post.get("post_id") or post.get("content_id") or stable_id("museon_post_source", campaign_id, username, museon_post_published_at(post)))
            material_source_id = str(post.get("content_id") or post_source_id)
            reelfarm_video_id = f"museon:{campaign_id}:{material_source_id}"
            reelfarm_post_id = f"museon:{campaign_id}:{post_source_id}"
            material_id = stable_id("museon_material", reelfarm_video_id)
            post_id = stable_id("museon_post", reelfarm_post_id)
            metrics = museon_post_metrics(post)
            published_at = museon_post_published_at(post)
            images = museon_post_images(post)

            account_ids.add(account_id)
            material_count += 1
            post_count += 1

            upsert_row(
                conn,
                "accounts",
                {
                    "id": account_id,
                    "product_market_channel_id": product_market_channel_id,
                    "source": "museon_clone",
                    "source_account_id": account_source_id,
                    "reelfarm_account_id": account_source_id,
                    "username": account.get("username") or username,
                    "display_name": account.get("display_name") or account.get("username") or username,
                    "avatar_url": account.get("avatar_url") or "",
                    "status": account.get("status") or "active",
                },
                ["product_market_channel_id", "reelfarm_account_id"],
            )
            upsert_row(
                conn,
                "automations",
                {
                    "id": automation_id,
                    "product_market_channel_id": product_market_channel_id,
                    "account_id": account_id,
                    "source": "museon_clone",
                    "source_automation_id": automation_source_id,
                    "reelfarm_automation_id": automation_source_id,
                    "name": campaign_name,
                    "status": "active",
                    "schedule": "[]",
                    "settings_json": db_json({"source": "museon_clone", "campaign": campaign, "account": account}),
                    "post_mode": "RPA",
                    "publish_method": "rpa",
                    "created_at": campaign.get("created_at") or "",
                    "synced_at": synced_at,
                },
                ["reelfarm_automation_id"],
            )
            upsert_row(
                conn,
                "materials",
                {
                    "id": material_id,
                    "automation_id": automation_id,
                    "product_market_channel_id": product_market_channel_id,
                    "account_id": account_id,
                    "concept_id": None,
                    "format_id": None,
                    "source": "museon_clone",
                    "source_material_id": reelfarm_video_id,
                    "reelfarm_video_id": reelfarm_video_id,
                    "video_type": post.get("content_type") or "slideshow",
                    "hook": post.get("title") or post.get("description") or "",
                    "prompt": post.get("caption") or post.get("description") or "",
                    "images_json": db_json(images),
                    "slide_count": int_or_none(post.get("slide_count")) or len(images),
                    "status": post.get("status") or "",
                    "created_at": post.get("created_at") or published_at or "",
                    "finished_at": post.get("finished_at") or "",
                    "synced_at": synced_at,
                },
                ["reelfarm_video_id"],
            )
            upsert_row(
                conn,
                "posts",
                {
                    "id": post_id,
                    "material_id": material_id,
                    "account_id": account_id,
                    "source": "museon_clone",
                    "source_post_id": reelfarm_post_id,
                    "reelfarm_post_id": reelfarm_post_id,
                    "status": post.get("status") or "",
                    "title": post.get("title") or post.get("description") or "",
                    "published_at": published_at,
                    "published_at_readable": readable_utc_datetime(published_at),
                    "view_count": metrics["view_count"],
                    "like_count": metrics["like_count"],
                    "comment_count": metrics["comment_count"],
                    "share_count": metrics["share_count"],
                    "bookmark_count": metrics["bookmark_count"],
                    "synced_at": synced_at,
                },
                ["reelfarm_post_id"],
            )
            snapshot_date = utc_snapshot_date()
            upsert_row(
                conn,
                "post_daily_snapshots",
                {
                    "id": stable_id("post_daily_snapshot", post_id, snapshot_date),
                    "post_id": post_id,
                    "snapshot_date": snapshot_date,
                    "view_count": metrics["view_count"],
                    "like_count": metrics["like_count"],
                    "comment_count": metrics["comment_count"],
                    "share_count": metrics["share_count"],
                    "bookmark_count": metrics["bookmark_count"],
                    "synced_at": synced_at,
                },
                ["post_id", "snapshot_date"],
            )
        conn.commit()

    return {
        "ok": True,
        "source": "museon_clone",
        "product_code": product_code,
        "country_code": country_code,
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "creator_count": len(account_ids),
        "material_count": material_count,
        "post_count": post_count,
        "synced_at": synced_at,
        "duration_total_seconds": round(time.perf_counter() - started, 3),
    }


def query_museon_clone_accounts(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if not date_from and not date_to:
        date_from, date_to = query_days_window(query)
    campaign = museon_clone_campaign(product_code, country_code)
    if not campaign:
        return []

    campaign_id = campaign.get("id")
    posts = museon_all_posts(campaign_id, date_from, date_to)
    grouped = {}
    for post in posts:
        account = museon_account_from_post(post)
        username_key = normalize_username(account.get("username"))
        if not username_key:
            continue
        row = grouped.setdefault(username_key, {
            "account": account,
            "posts": 0,
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "bookmarks": 0,
            "latest_post_at": "",
        })
        row["posts"] += 1
        metrics = museon_post_metrics(post)
        row["views"] += metrics["view_count"]
        row["likes"] += metrics["like_count"]
        row["comments"] += metrics["comment_count"]
        row["shares"] += metrics["share_count"]
        row["bookmarks"] += metrics["bookmark_count"]
        published_at = post.get("published_at") or post.get("created_at") or ""
        if published_at and published_at > row["latest_post_at"]:
            row["latest_post_at"] = published_at

    rows = []
    for username_key, grouped_row in grouped.items():
        account = grouped_row["account"]
        synthetic_id = f"museon:{product_code}:{country_code}:{username_key}"
        rows.append({
            "account_id": synthetic_id,
            "reelfarm_account_id": None,
            "museon_account_id": account.get("id"),
            "username": account.get("username"),
            "display_name": account.get("display_name") or account.get("username"),
            "avatar_url": account.get("avatar_url"),
            "status": campaign.get("status") or "active",
            "automation_count": 1,
            "automation_name": campaign.get("name") or campaign.get("title"),
            "automation_names": campaign.get("name") or campaign.get("title"),
            "publish_method": "rpa",
            "material_count": grouped_row["posts"],
            "post_count": grouped_row["posts"],
            "total_views": grouped_row["views"],
            "total_likes": grouped_row["likes"],
            "total_comments": grouped_row["comments"],
            "total_shares": grouped_row["shares"],
            "total_bookmarks": grouped_row["bookmarks"],
            "latest_post_at": grouped_row["latest_post_at"],
            "last_synced_at": grouped_row["latest_post_at"],
            "data_source": "museon_clone",
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name") or campaign.get("title"),
        })
    return attach_account_issues(sorted(rows, key=lambda row: (int(row.get("total_views") or 0), int(row.get("post_count") or 0)), reverse=True))


def reelfarm_detailed_rows_for_username(product_code, country_code, username):
    username_key = normalize_username(username)
    if not username_key:
        return []
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT {detailed_select()}
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}
              AND m.code = {placeholder}
              AND LOWER(REPLACE(acc.username, '@', '')) = {placeholder}
              AND post.id IS NOT NULL
            ORDER BY post.published_at DESC
            LIMIT 500
            """,
            ("TIKTOK", product_code, country_code, username_key),
        ).fetchall()
    return [detailed_row(row) for row in rows]


def nearest_reelfarm_row(museon_post, rf_rows):
    published = parse_iso_datetime(museon_post.get("published_at"))
    if not published:
        return None
    best = None
    best_delta = 10**9
    for row in rf_rows:
        candidate = parse_iso_datetime((row.get("post") or {}).get("published_at"))
        if not candidate:
            continue
        delta = abs((candidate - published).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best = row
    return best if best and best_delta <= 15 * 60 else None


def museon_post_to_detailed_row(post, product, country, rf_match=None):
    account = museon_account_from_post(post)
    metrics = museon_post_metrics(post)
    published_at = post.get("published_at") or post.get("created_at") or ""
    content_id = post.get("content_id") or post.get("id")
    images = museon_post_images(post)
    if not images and content_id:
        images = museon_content_download_images(content_id)
    base = rf_match or {
        "product": product,
        "country": country,
        "market": country,
        "account": {},
        "automation": {},
        "material": {},
        "post": {},
        "metrics": {},
    }
    material = dict(base.get("material") or {})
    material.update({
        "id": material.get("id") or post.get("content_id") or post.get("id"),
        "reelfarm_video_id": material.get("reelfarm_video_id") or post.get("content_id"),
        "video_type": material.get("video_type") or post.get("content_type") or "slideshow",
        "hook": material.get("hook") or post.get("title") or post.get("description"),
        "prompt": material.get("prompt") or post.get("description"),
        "slideshow_images": material.get("slideshow_images") or images,
        "slide_count": material.get("slide_count") or len(images),
        "status": material.get("status") or post.get("status"),
    })
    return {
        "product": product,
        "country": country,
        "market": country,
        "account": {
            "id": (base.get("account") or {}).get("id") or f"museon:{product.get('code')}:{country.get('code')}:{normalize_username(account.get('username'))}",
            "reelfarm_account_id": (base.get("account") or {}).get("reelfarm_account_id"),
            "museon_account_id": account.get("id"),
            "username": account.get("username"),
            "display_name": account.get("display_name"),
            "avatar_url": account.get("avatar_url") or (base.get("account") or {}).get("avatar_url"),
            "status": account.get("status"),
        },
        "automation": base.get("automation") or {},
        "material": material,
        "post": {
            "id": post.get("id"),
            "reelfarm_post_id": (base.get("post") or {}).get("reelfarm_post_id"),
            "museon_post_id": post.get("id"),
            "status": post.get("status"),
            "title": post.get("title") or post.get("description"),
            "published_at": published_at,
            "published_at_readable": readable_utc_datetime(published_at),
            "synced_at": post.get("synced_at") or post.get("updated_at"),
        },
        "metrics": metrics,
    }


def query_museon_clone_account_posts(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    account_id = query_value(query, "account_id")
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if not date_from and not date_to:
        date_from, date_to = query_days_window(query)
    limit, offset = query_limit_offset(query)
    campaign = museon_clone_campaign(product_code, country_code)
    if not campaign:
        return [], pagination_payload(limit, offset, [], 0)
    username = account_id
    if account_id.startswith("museon:"):
        username = account_id.split(":")[-1]
    page = (offset // limit) + 1
    posts, total = museon_posts(campaign.get("id"), date_from, date_to, username=username, page=page, page_size=limit)
    product, country = local_product_country_context(product_code, country_code)
    rows = []
    for post in posts:
        rows.append(museon_post_to_detailed_row(post, product, country))
    return rows, pagination_payload(limit, offset, rows, total)


def query_reelfarm_accounts(query):
    return query_accounts_runtime(query)


def query_accounts(query):
    return query_reelfarm_accounts(query)


def beijing_day_window(now=None):
    return beijing_day_window_impl(now)


def product_country_lookup():
    return publish_check_product_country_lookup_runtime()


def publish_check_accounts(product_code, country_code, utc_start, utc_end):
    return publish_check_accounts_runtime(product_code, country_code, utc_start, utc_end)


def run_publish_check():
    return run_publish_check_runtime()


def publish_check_reminder_text(result):
    return publish_check_reminder_text_impl(result)


def daily_feishu_service():
    return daily_feishu_runtime.daily_feishu_service()


def send_feishu_message(message):
    return daily_feishu_service().send_feishu_message(message)


def daily_feishu_report_payload(report_date=""):
    return daily_feishu_service().report_payload(report_date)


def daily_feishu_llm_api_key():
    return daily_feishu_service().llm_api_key()


def daily_feishu_llm_model(model=""):
    return daily_feishu_service().selected_llm_model(model)


def fallback_llm_models():
    return daily_feishu_service().selectable_llm_models()


def llm_models_payload():
    return daily_feishu_service().llm_models_payload()


def call_daily_feishu_llm(messages, model=""):
    return daily_feishu_service().call_daily_feishu_llm(messages, model)


def daily_feishu_ai_analysis(report_date="", model="", report=None, require_config=False):
    return daily_feishu_service().ai_analysis(report_date, model, report, require_config)


def send_daily_feishu_report(report_date="", include_ai=False, model="", require_synced=False):
    return daily_feishu_service().send_report(report_date, include_ai, model, require_synced)


def send_publish_check_reminder():
    return send_publish_check_reminder_runtime()


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


def find_open_port(start_port=8765):
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available local port found.")



def run_fastapi_server():
    # When server.py is executed as a script, expose this module under its import
    # name so api.index imports the same runtime state instead of loading a
    # second copy of server.py as "server".
    sys.modules.setdefault("server", sys.modules[__name__])

    try:
        import uvicorn
    except ImportError as error:
        raise RuntimeError("uvicorn is required to run the local API server. Run: pip install -r requirements.txt") from error

    init_db()
    cloud_port = os.environ.get("PORT", "").strip()
    port = int(cloud_port) if cloud_port else find_open_port()
    host = "0.0.0.0" if cloud_port else "127.0.0.1"
    url = f"http://127.0.0.1:{port}/" if not cloud_port else f"http://{host}:{port}/"
    print(f"Management Table is running: {url}")
    print(f"Database backend: {'Postgres' if using_postgres() else f'SQLite ({DB_PATH})'}")
    print("API framework: FastAPI")
    if not cloud_port:
        webbrowser.open(url)
    uvicorn.run("api.index:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_fastapi_server()
