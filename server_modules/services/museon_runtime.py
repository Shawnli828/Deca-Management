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
from server_modules.data_query_helpers import (
    pagination_payload,
    post_datetime_bound as post_datetime_bound_impl,
    query_days_window,
    query_limit_offset,
    query_value,
    relational_base_from,
)
from server_modules.detailed_rows import detailed_row, detailed_select
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
from server_modules.time_windows import business_material_day_window, parse_iso_datetime


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


def reelfarm_account_lookup(product_code, country_code, query_reelfarm_accounts_fn):
    lookup = {}
    query = {"product_code": [product_code], "country_code": [country_code]}
    for row in query_reelfarm_accounts_fn(query):
        username = normalize_username(row.get("username") or row.get("display_name"))
        if username:
            lookup[username] = row
    return lookup


def query_clone_accounts(query, attach_account_issues_fn=lambda rows: rows):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if not date_from and not date_to:
        date_from, date_to = query_days_window(query)
    campaign = clone_campaign(product_code, country_code)
    if not campaign:
        return []

    campaign_id = campaign.get("id")
    posts = all_posts(campaign_id, date_from, date_to)
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
    sorted_rows = sorted(
        rows,
        key=lambda row: (int(row.get("total_views") or 0), int(row.get("post_count") or 0)),
        reverse=True,
    )
    return attach_account_issues_fn(sorted_rows)


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


def post_to_detailed_row(post, product, country, rf_match=None):
    account = museon_account_from_post(post)
    metrics = museon_post_metrics(post)
    published_at = post.get("published_at") or post.get("created_at") or ""
    content_id = post.get("content_id") or post.get("id")
    images = museon_post_images(post)
    if not images and content_id:
        images = content_download_images(content_id)
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


def query_clone_account_posts(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    account_id = query_value(query, "account_id")
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if not date_from and not date_to:
        date_from, date_to = query_days_window(query)
    limit, offset = query_limit_offset(query)
    campaign = clone_campaign(product_code, country_code)
    if not campaign:
        return [], pagination_payload(limit, offset, [], 0)
    username = account_id
    if account_id.startswith("museon:"):
        username = account_id.split(":")[-1]
    page = (offset // limit) + 1
    post_rows, total = posts(campaign.get("id"), date_from, date_to, username=username, page=page, page_size=limit)
    product, country = local_product_country_context(product_code, country_code)
    rows = [post_to_detailed_row(post, product, country) for post in post_rows]
    return rows, pagination_payload(limit, offset, rows, total)
