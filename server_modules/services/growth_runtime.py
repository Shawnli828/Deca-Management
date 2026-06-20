from datetime import datetime, timedelta, timezone

from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema, make_ssl_context
from server_modules.common import stable_id
from server_modules.data_query_helpers import query_value, relational_base_from, row_dict
from server_modules.db_core import upsert_row as upsert_row_impl
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
    mixpanel_event_daily_counts as mixpanel_event_daily_counts_impl,
    mixpanel_event_user_unique_query_count as mixpanel_event_user_unique_query_count_impl,
)
from server_modules.mixpanel_utils import product_mixpanel_config, product_mixpanel_event_name
from server_modules.reelfarm_utils import (
    reelfarm_expected_automation_condition,
    reelfarm_schedule_slot_count,
)
from server_modules.settings import MIXPANEL_REGION, MIXPANEL_TIMEZONE_NAME, REPORT_TIMEZONE_NAME
from server_modules.time_windows import (
    business_material_date_for_utc_datetime,
    growth_report_windows,
    mixpanel_timezone,
    parse_iso_datetime,
    report_date_for_utc_datetime,
    report_day_window,
    report_timezone,
    source_dates_for_utc_window,
)


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


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
