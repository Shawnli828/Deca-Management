import time
from datetime import datetime, timezone

from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema, load_data, make_ssl_context
from server_modules.common import (
    code_from_name,
    db_json,
    int_or_none,
    normalize_username,
    parse_json_list,
    readable_utc_datetime,
    stable_id,
    utc_snapshot_date,
)
from server_modules.data_query_helpers import post_datetime_bound as post_datetime_bound_impl
from server_modules.db_core import upsert_row as upsert_row_impl
from server_modules.museon_client import (
    museon_all_posts as museon_all_posts_impl,
    museon_campaigns as museon_campaigns_impl,
    museon_clone_campaign as museon_clone_campaign_impl,
    museon_clone_campaigns_for_product as museon_clone_campaigns_for_product_impl,
    museon_content_download_images as museon_content_download_images_impl,
    museon_posts as museon_posts_impl,
    museon_request as museon_request_impl,
)
from server_modules.museon_utils import (
    museon_account_from_post,
    museon_content_id_from_material_source,
    museon_post_images,
    museon_post_metrics,
)
from server_modules.product_config import COUNTRY_CODES, country_code_for, product_code_for
from server_modules.settings import MUSEON_API_KEY, MUSEON_BASE_URL, MUSEON_USER_AGENT, MUSEON_WORKSPACE_ID
from server_modules.time_windows import business_material_day_window


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


def post_datetime_bound(value, end=False):
    return post_datetime_bound_impl(value, end, business_material_day_window=business_material_day_window)


def request(path, params=None):
    return museon_request_impl(
        path,
        params,
        api_key=MUSEON_API_KEY,
        base_url=MUSEON_BASE_URL,
        user_agent=MUSEON_USER_AGENT,
        make_ssl_context=make_ssl_context,
    )


def campaigns(force=False):
    return museon_campaigns_impl(
        request_fn=request,
        workspace_id=MUSEON_WORKSPACE_ID,
        force=force,
    )


def clone_campaign(product_code, country_code):
    return museon_clone_campaign_impl(
        product_code,
        country_code,
        campaigns_fn=campaigns,
    )


def clone_campaigns_for_product(product_code, country_code=""):
    return museon_clone_campaigns_for_product_impl(
        product_code,
        country_code,
        products=load_data(),
        country_codes=COUNTRY_CODES,
        code_from_name=code_from_name,
        clone_campaign_fn=clone_campaign,
    )


def posts(campaign_id, date_from="", date_to="", username="", page=1, page_size=100, sort=""):
    return museon_posts_impl(
        campaign_id,
        date_from,
        date_to,
        username,
        page,
        page_size,
        sort,
        request_fn=request,
        post_datetime_bound=post_datetime_bound,
    )


def all_posts(campaign_id, date_from="", date_to="", max_pages=40):
    return museon_all_posts_impl(
        campaign_id,
        date_from,
        date_to,
        max_pages,
        posts_fn=posts,
    )


def content_download_images(content_id):
    return museon_content_download_images_impl(content_id, request_fn=request)


def hydrate_images_for_rows(conn, row_data_list):
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
        images = content_download_images(content_id)
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


def post_published_at(post):
    return post.get("published_at") or post.get("created_at") or post.get("posted_at") or ""


def sync_clone_country(product_id="", country_id="", product_code="", country_code=""):
    product, country, product_code, country_code = local_product_country_record(product_id, country_id, product_code, country_code)
    if not product_code or not country_code:
        raise ValueError("Missing product_code or country_code.")

    started = time.perf_counter()
    synced_at = datetime.now(timezone.utc).isoformat()
    campaign = clone_campaign(product_code, country_code)
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

    post_rows = all_posts(campaign.get("id"), max_pages=0)
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

        for post in post_rows:
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
            post_source_id = str(post.get("id") or post.get("post_id") or post.get("content_id") or stable_id("museon_post_source", campaign_id, username, post_published_at(post)))
            material_source_id = str(post.get("content_id") or post_source_id)
            reelfarm_video_id = f"museon:{campaign_id}:{material_source_id}"
            reelfarm_post_id = f"museon:{campaign_id}:{post_source_id}"
            material_id = stable_id("museon_material", reelfarm_video_id)
            post_id = stable_id("museon_post", reelfarm_post_id)
            metrics = museon_post_metrics(post)
            published_at = post_published_at(post)
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
