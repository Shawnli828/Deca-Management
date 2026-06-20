from datetime import datetime, timezone

from server_modules.account_issues import (
    apply_zero_play_issues as apply_zero_play_issues_impl,
    collect_zero_play_issue_candidate,
)
from server_modules.app_runtime import (
    connect_db,
    db_placeholder,
    init_relational_schema,
    load_data,
    using_postgres,
)
from server_modules.automation_naming import parse_concept_format_from_automation
from server_modules.common import db_json, int_or_none, stable_id, utc_snapshot_date
from server_modules.db_core import upsert_row as upsert_row_impl
from server_modules.product_config import country_code_for, product_code_for
from server_modules.reelfarm_lifecycle import (
    active_tiktok_automation_account_ids as active_tiktok_automation_account_ids_impl,
    mark_missing_reelfarm_automations as mark_missing_reelfarm_automations_impl,
)
from server_modules.reelfarm_utils import (
    reelfarm_automation_is_active,
    reelfarm_post_mode,
    reelfarm_publish_method,
)
from server_modules.schema import relational_table_counts as relational_table_counts_impl
from server_modules.time_windows import business_date_string


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


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


def apply_zero_play_issues(conn, candidates, synced_at):
    return apply_zero_play_issues_impl(
        conn,
        candidates,
        synced_at,
        placeholder=db_placeholder(),
        upsert_row=upsert_row,
        active_tiktok_automation_account_ids=active_tiktok_automation_account_ids,
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
