from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema
from server_modules.common import stable_id
from server_modules.data_query_helpers import relational_base_from, row_dict
from server_modules.db_core import upsert_row as upsert_row_impl
from server_modules.domain.growth import material_daily_stats_from_rows
from server_modules.reelfarm_utils import (
    reelfarm_expected_automation_condition,
    reelfarm_schedule_slot_count,
)
from server_modules.time_windows import (
    business_material_date_for_utc_datetime,
    parse_iso_datetime,
    report_date_for_utc_datetime,
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
    return material_daily_stats_from_rows(
        [row_dict(row) for row in rows],
        parse_iso_datetime,
        business_material_date_for_utc_datetime,
    )


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


def upsert_product_daily_growth_snapshot(record):
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(conn, "product_daily_growth_snapshots", record, ["product_code", "report_date"])
        conn.commit()
    return record


def upsert_product_daily_growth_snapshots(records):
    with connect_db() as conn:
        init_relational_schema(conn)
        for record in records:
            upsert_row(conn, "product_daily_growth_snapshots", record, ["product_code", "report_date"])
        conn.commit()
    return records
