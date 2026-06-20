from datetime import datetime, timedelta, timezone

from server_modules.app_runtime import connect_db, data_source_channel_code, db_placeholder, init_relational_schema
from server_modules.common import int_or_none, parse_json_list
from server_modules.data_query_helpers import (
    common_where as common_where_impl,
    query_days_snapshot_window,
    query_filters,
    query_value,
    relational_base_from,
    row_dict,
)
from server_modules.reelfarm_utils import reelfarm_dashboard_automation_condition
from server_modules.services.tag_runtime import account_issues_payload
from server_modules.time_windows import business_material_day_window, parse_iso_datetime


def post_common_where(query, date_column="post.published_at", include_post_dates=True):
    return common_where_impl(
        query,
        date_column,
        include_post_dates,
        placeholder=db_placeholder(),
        data_source_channel_code=data_source_channel_code,
        business_material_day_window=business_material_day_window,
    )


def stored_reelfarm_country(product_code, market_code):
    product_code = str(product_code or "").strip().upper()
    market_code = str(market_code or "").strip().upper()
    if not product_code or not market_code:
        raise ValueError("Missing product_code or country_code.")

    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                a.id AS automation_internal_id,
                a.reelfarm_automation_id,
                a.name AS automation_name,
                a.status AS automation_status,
                a.schedule AS automation_schedule,
                a.post_mode AS automation_post_mode,
                a.publish_method AS automation_publish_method,
                a.created_at AS automation_created_at,
                acc.reelfarm_account_id,
                acc.username AS account_username,
                acc.display_name AS account_name,
                acc.avatar_url AS account_image,
                mat.reelfarm_video_id,
                mat.created_at AS material_created_at,
                mat.finished_at AS material_finished_at,
                mat.status AS material_status,
                mat.video_type,
                mat.hook,
                mat.prompt,
                mat.images_json,
                mat.slide_count,
                post.reelfarm_post_id,
                post.status AS post_status,
                post.title AS post_title,
                post.published_at,
                post.published_at_readable,
                post.view_count,
                post.like_count,
                post.comment_count,
                post.share_count,
                post.bookmark_count
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            JOIN automations a ON a.product_market_channel_id = pmc.id
            LEFT JOIN accounts acc ON acc.id = a.account_id
            LEFT JOIN materials mat ON mat.automation_id = a.id
            LEFT JOIN posts post ON post.material_id = mat.id
            WHERE p.code = {placeholder}
              AND m.code = {placeholder}
              AND ch.code = {placeholder}
              AND {reelfarm_dashboard_automation_condition("a")}
            ORDER BY a.name, mat.created_at DESC, post.published_at DESC
            """,
            (product_code, market_code, "TIKTOK"),
        ).fetchall()

    cards_by_id = {}
    for row in rows:
        automation_id = row["reelfarm_automation_id"]
        if not automation_id:
            continue

        if automation_id not in cards_by_id:
            account_id = row["reelfarm_account_id"] or ""
            cards_by_id[automation_id] = {
                "automation": {
                    "automation_id": automation_id,
                    "title": row["automation_name"],
                    "status": row["automation_status"],
                    "tiktok_account_id": account_id,
                    "schedule": parse_json_list(row["automation_schedule"]),
                    "post_mode": row["automation_post_mode"] or "",
                    "publish_method": row["automation_publish_method"] or "api",
                    "created_at": row["automation_created_at"],
                },
                "account": {
                    "tiktok_account_id": account_id,
                    "account_name": row["account_name"],
                    "account_username": row["account_username"],
                    "account_image": row["account_image"],
                },
                "videos": [],
                "video_total": 0,
                "posts": [],
                "post_statistics": {},
                "errors": {"videos": None, "posts": None},
            }

        card = cards_by_id[automation_id]
        video_id = row["reelfarm_video_id"]
        if video_id and not any(str(video.get("video_id")) == str(video_id) for video in card["videos"]):
            card["videos"].append(
                {
                    "video_id": video_id,
                    "created_at": row["material_created_at"],
                    "finished_at": row["material_finished_at"],
                    "status": row["material_status"],
                    "finished": row["material_status"] == "Finished",
                    "failed": False,
                    "video_type": row["video_type"],
                    "video_url": None,
                    "slideshow_images": parse_json_list(row["images_json"]),
                    "slide_count": int_or_none(row["slide_count"]) or 0,
                    "hook": row["hook"] or "",
                    "prompt": row["prompt"] or "",
                }
            )

        post_id = row["reelfarm_post_id"]
        if post_id and not any(str(post.get("post_id")) == str(post_id) for post in card["posts"]):
            card["posts"].append(
                {
                    "post_id": post_id,
                    "video_id": video_id,
                    "status": row["post_status"],
                    "title": row["post_title"],
                    "account_username": row["account_username"],
                    "published_at": row["published_at"],
                    "published_at_meta": row["published_at"],
                    "published_at_readable": row["published_at_readable"],
                    "view_count": row["view_count"],
                    "like_count": row["like_count"],
                    "comment_count": row["comment_count"],
                    "share_count": row["share_count"],
                    "bookmark_count": row["bookmark_count"],
                }
            )

    cards = list(cards_by_id.values())
    for card in cards:
        card["video_total"] = len(card["videos"])

    return {
        "prefix": f"{market_code}-{product_code}",
        "count": len(cards),
        "cards": cards,
    }


def query_summary(query):
    where_sql, params = post_common_where(query)
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"""
            SELECT
                COUNT(DISTINCT p.id) AS products,
                COUNT(DISTINCT m.id) AS countries,
                COUNT(DISTINCT acc.id) AS accounts,
                COUNT(DISTINCT a.id) AS automations,
                COUNT(DISTINCT mat.id) AS materials,
                COUNT(DISTINCT post.id) AS posts,
                COALESCE(SUM(post.view_count), 0) AS total_views,
                COALESCE(SUM(post.like_count), 0) AS total_likes,
                COALESCE(SUM(post.comment_count), 0) AS total_comments,
                COALESCE(SUM(post.share_count), 0) AS total_shares,
                COALESCE(SUM(post.bookmark_count), 0) AS total_bookmarks,
                MAX(COALESCE(post.synced_at, mat.synced_at, a.synced_at)) AS last_synced_at
            {relational_base_from()}
            WHERE {where_sql}
            """,
            tuple(params),
        ).fetchone()
    return row_dict(row)


def query_country_cards(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    return stored_reelfarm_country(product_code, country_code)


def query_countries(query):
    where_sql, params = post_common_where(query, include_post_dates=False)
    visibility_sql = ""
    if data_source_channel_code(query_value(query, "source")) == "TIKTOK":
        visibility_sql = f" AND {reelfarm_dashboard_automation_condition('a')}"
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                p.id AS product_id,
                p.code AS product_code,
                p.name AS product_name,
                m.id AS market_id,
                m.id AS country_id,
                m.code AS market_code,
                m.code AS country_code,
                m.name AS country_name,
                COUNT(DISTINCT acc.id) AS creator_count,
                COUNT(DISTINCT a.id) AS automation_count,
                COUNT(DISTINCT mat.id) AS material_count,
                COUNT(DISTINCT post.id) AS post_count,
                COALESCE(SUM(post.view_count), 0) AS total_views,
                COALESCE(SUM(post.like_count), 0) AS total_likes,
                COALESCE(SUM(post.comment_count), 0) AS total_comments,
                COALESCE(SUM(post.share_count), 0) AS total_shares,
                COALESCE(SUM(post.bookmark_count), 0) AS total_bookmarks,
                MAX(COALESCE(post.synced_at, mat.synced_at, a.synced_at)) AS last_synced_at
            {relational_base_from()}
            WHERE {where_sql}{visibility_sql}
            GROUP BY p.id, p.code, p.name, m.id, m.code, m.name
            ORDER BY p.name, m.code
            """,
            tuple(params),
        ).fetchall()

    rows = [row_dict(row) for row in rows]
    ids = [str(row.get("account_id") or "").strip() for row in rows if str(row.get("account_id") or "").strip()]
    issue_map = account_issues_payload(ids).get("issues", {}) if ids else {}
    for row in rows:
        row["issues"] = issue_map.get(row.get("account_id"), [])
    return rows


def query_product_kpis(query):
    channel_code = data_source_channel_code(query_value(query, "source"))
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    if not product_code:
        raise ValueError("product_code is required.")
    placeholder = db_placeholder()
    now_utc = datetime.now(timezone.utc)
    beijing = timezone(timedelta(hours=8))
    current_local = now_utc.astimezone(beijing)
    today_start_local = datetime(current_local.year, current_local.month, current_local.day, tzinfo=beijing)
    yesterday_start_local = today_start_local - timedelta(days=1)
    seven_start_local = yesterday_start_local - timedelta(days=6)
    seven_end_local = today_start_local
    yesterday_start = yesterday_start_local.astimezone(timezone.utc).isoformat()
    yesterday_end = today_start_local.astimezone(timezone.utc).isoformat()
    seven_start = seven_start_local.astimezone(timezone.utc).isoformat()
    seven_end = seven_end_local.astimezone(timezone.utc).isoformat()
    market_filter = ""
    filter_params = [channel_code, product_code]
    if country_code:
        market_filter = f" AND m.code = {placeholder}"
        filter_params.append(country_code)
    visibility_filter = ""
    if channel_code == "TIKTOK":
        visibility_filter = f" AND {reelfarm_dashboard_automation_condition('a')}"
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"""
            SELECT
                COUNT(DISTINCT CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN acc.id END) AS today_creators,
                COUNT(DISTINCT CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.id END) AS today_posts,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.view_count ELSE 0 END), 0) AS today_views,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.like_count ELSE 0 END), 0) AS today_likes,
                COUNT(DISTINCT CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN acc.id END) AS seven_day_creators,
                COUNT(DISTINCT CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.id END) AS seven_day_posts,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.view_count ELSE 0 END), 0) AS seven_day_views,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.like_count ELSE 0 END), 0) AS seven_day_likes,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.comment_count ELSE 0 END), 0) AS seven_day_comments,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.share_count ELSE 0 END), 0) AS seven_day_shares,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.bookmark_count ELSE 0 END), 0) AS seven_day_bookmarks
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}{market_filter}{visibility_filter}
              AND post.id IS NOT NULL
            """,
            (
                yesterday_start, yesterday_end,
                yesterday_start, yesterday_end,
                yesterday_start, yesterday_end,
                yesterday_start, yesterday_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                *filter_params,
            ),
        ).fetchone()
        daily_rows = conn.execute(
            f"""
            SELECT acc.id AS account_id, post.published_at AS published_at
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}{market_filter}
              AND post.published_at >= {placeholder}
              AND post.published_at < {placeholder}
              AND post.id IS NOT NULL
            """,
            (*filter_params, seven_start, seven_end),
        ).fetchall()

    data = row_dict(row)
    daily_creator_sets = {
        (seven_start_local + timedelta(days=day_index)).date().isoformat(): set()
        for day_index in range(7)
    }
    for daily_row in daily_rows:
        daily_data = row_dict(daily_row)
        parsed = parse_iso_datetime(daily_data.get("published_at"))
        if not parsed:
            continue
        local_day = parsed.astimezone(beijing).date().isoformat()
        if local_day in daily_creator_sets and daily_data.get("account_id"):
            daily_creator_sets[local_day].add(daily_data["account_id"])
    average_daily_creators = sum(len(accounts) for accounts in daily_creator_sets.values()) / 7
    today_creators = int(data.get("today_creators") or 0)
    today_posts = int(data.get("today_posts") or 0)
    today_views = int(data.get("today_views") or 0)
    today_likes = int(data.get("today_likes") or 0)
    seven_creators = int(data.get("seven_day_creators") or 0)
    seven_posts = int(data.get("seven_day_posts") or 0)
    seven_views = int(data.get("seven_day_views") or 0)
    seven_likes = int(data.get("seven_day_likes") or 0)
    interactions = (
        seven_likes
        + int(data.get("seven_day_comments") or 0)
        + int(data.get("seven_day_shares") or 0)
        + int(data.get("seven_day_bookmarks") or 0)
    )
    return {
        "product_code": product_code,
        "country_code": country_code or None,
        "today": {
            "creators": today_creators,
            "posts": today_posts,
            "views": today_views,
            "likes": today_likes,
            "average_views": round(today_views / today_posts) if today_posts else 0,
            "utc_window": {"start": yesterday_start, "end": yesterday_end},
        },
        "seven_day": {
            "creators": seven_creators,
            "posts": seven_posts,
            "views": seven_views,
            "likes": seven_likes,
            "average_creators": average_daily_creators,
            "average_posts": seven_posts / 7,
            "average_views": round(seven_views / seven_posts) if seven_posts else 0,
            "average_views_per_day": seven_views / 7,
            "average_likes": seven_likes / 7,
            "average_er": (interactions / seven_views * 100) if seven_views else 0,
            "interactions": interactions,
            "utc_window": {"start": seven_start, "end": seven_end},
        },
    }


def query_product_rollups(query):
    rows = query_countries(query)
    product_map = {}
    for row in rows:
        product_code = str(row.get("product_code") or "").upper()
        item = product_map.setdefault(product_code, {
            "product_id": row.get("product_id"),
            "product_code": product_code,
            "product_name": row.get("product_name"),
            "creator_count": 0,
            "material_count": 0,
            "post_count": 0,
            "last_synced_at": "",
            "countries": [],
        })
        country = {
            "country_id": row.get("country_id") or row.get("market_id"),
            "country_code": row.get("country_code") or row.get("market_code"),
            "country_name": row.get("country_name"),
            "creator_count": int(row.get("creator_count") or 0),
            "material_count": int(row.get("material_count") or 0),
            "post_count": int(row.get("post_count") or 0),
            "last_synced_at": row.get("last_synced_at") or "",
        }
        item["countries"].append(country)
        item["creator_count"] += country["creator_count"]
        item["material_count"] += country["material_count"]
        item["post_count"] += country["post_count"]
        if country["last_synced_at"] and country["last_synced_at"] > item["last_synced_at"]:
            item["last_synced_at"] = country["last_synced_at"]
    return list(product_map.values())


def query_daily_metrics(query):
    filters = query_filters(query)
    if not filters.get("date_from") and not filters.get("date_to"):
        date_from, date_to = query_days_snapshot_window(query)
        filters["date_from"] = date_from or filters.get("date_from")
        filters["date_to"] = date_to or filters.get("date_to")

    placeholder = db_placeholder()
    where_sql, params = post_common_where(query, date_column="snap.snapshot_date", include_post_dates=False)
    if filters.get("date_from"):
        where_sql += f" AND snap.snapshot_date >= {placeholder}"
        params.append(filters["date_from"])
    if filters.get("date_to"):
        where_sql += f" AND snap.snapshot_date <= {placeholder}"
        params.append(filters["date_to"])

    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                snap.snapshot_date,
                COUNT(DISTINCT post.id) AS post_count,
                COALESCE(SUM(snap.view_count), 0) AS views,
                COALESCE(SUM(snap.like_count), 0) AS likes,
                COALESCE(SUM(snap.comment_count), 0) AS comments,
                COALESCE(SUM(snap.share_count), 0) AS shares,
                COALESCE(SUM(snap.bookmark_count), 0) AS bookmarks
            FROM post_daily_snapshots snap
            JOIN posts post ON post.id = snap.post_id
            JOIN materials mat ON mat.id = post.material_id
            JOIN automations a ON a.id = mat.automation_id
            LEFT JOIN accounts acc ON acc.id = post.account_id
            JOIN product_market_channels pmc ON pmc.id = a.product_market_channel_id
            JOIN product_markets pm ON pm.id = pmc.product_market_id
            JOIN products p ON p.id = pm.product_id
            JOIN markets m ON m.id = pm.market_id
            JOIN channels ch ON ch.id = pmc.channel_id
            WHERE {where_sql}
            GROUP BY snap.snapshot_date
            ORDER BY snap.snapshot_date
            """,
            tuple(params),
        ).fetchall()

    data = [row_dict(row) for row in rows]
    previous = None
    for row in data:
        if previous:
            row["deltas"] = {
                "views": int(row.get("views") or 0) - int(previous.get("views") or 0),
                "likes": int(row.get("likes") or 0) - int(previous.get("likes") or 0),
                "comments": int(row.get("comments") or 0) - int(previous.get("comments") or 0),
                "shares": int(row.get("shares") or 0) - int(previous.get("shares") or 0),
                "bookmarks": int(row.get("bookmarks") or 0) - int(previous.get("bookmarks") or 0),
            }
        else:
            row["deltas"] = None
        previous = row
    return data
