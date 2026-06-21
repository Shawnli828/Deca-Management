from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema
from server_modules.data_query_helpers import relational_base_from, row_dict
from server_modules.reelfarm_utils import reelfarm_expected_automation_condition


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


def trend_row(report_date, view=0, download=0):
    return {
        "date": report_date,
        "view": int(view or 0),
        "download": int(download or 0),
    }


def empty_trend(report_dates):
    return {report_date: trend_row(report_date) for report_date in report_dates}


def daily_lifetime_trend(product_codes, dates):
    codes = []
    seen_codes = set()
    for code in product_codes or []:
        product_code = str(code or "").strip().upper()
        if product_code and product_code not in seen_codes:
            seen_codes.add(product_code)
            codes.append(product_code)

    report_dates = [str(value or "")[:10] for value in dates or [] if str(value or "")[:10]]
    if not codes or not report_dates:
        return {"overview": [], "products": {}}

    placeholder = db_placeholder()
    product_placeholders = ", ".join([placeholder] * len(codes))
    trends_by_code = {code: empty_trend(report_dates) for code in codes}

    with connect_db() as conn:
        init_relational_schema(conn)
        growth_rows = conn.execute(
            f"""
            SELECT product_code, report_date, total_views, download_count, onboarding_unique
            FROM product_daily_growth_snapshots
            WHERE product_code IN ({product_placeholders})
              AND report_date <= {placeholder}
            ORDER BY product_code, report_date
            """,
            (*codes, report_dates[-1]),
        ).fetchall()

        snapshot_rows = []
        if not growth_rows:
            snapshot_rows = conn.execute(
                f"""
                SELECT DISTINCT
                    p.code AS product_code,
                    post.id AS post_id,
                    snap.snapshot_date AS snapshot_date,
                    snap.view_count AS view_count
                {relational_base_from()}
                JOIN post_daily_snapshots snap ON snap.post_id = post.id
                WHERE p.code IN ({product_placeholders})
                  AND ch.code IN ('TIKTOK', 'MUSEON_CLONE')
                  AND post.id IS NOT NULL
                  AND snap.snapshot_date <= {placeholder}
                ORDER BY p.code, post.id, snap.snapshot_date
                """,
                (*codes, report_dates[-1]),
            ).fetchall()

    if growth_rows:
        daily = {}
        for row in growth_rows:
            item = row_dict(row)
            product_code = str(item.get("product_code") or "").strip().upper()
            report_date = str(item.get("report_date") or "")[:10]
            if not product_code or product_code not in trends_by_code or not report_date:
                continue
            entry = daily.setdefault(product_code, {}).setdefault(report_date, {"view": 0, "download": 0})
            entry["view"] += int(item.get("total_views") or 0)
            download = item.get("download_count")
            if download is None:
                download = item.get("onboarding_unique")
            entry["download"] += int(download or 0)

        for product_code, daily_rows in daily.items():
            running = {"view": 0, "download": 0}
            for report_date in sorted(daily_rows):
                if report_date <= report_dates[-1]:
                    running["view"] += daily_rows[report_date]["view"]
                    running["download"] += daily_rows[report_date]["download"]
                if report_date in trends_by_code[product_code]:
                    trends_by_code[product_code][report_date]["view"] = running["view"]
                    trends_by_code[product_code][report_date]["download"] = running["download"]

            for report_date in report_dates:
                if trends_by_code[product_code][report_date]["view"] or trends_by_code[product_code][report_date]["download"]:
                    continue
                trends_by_code[product_code][report_date]["view"] = sum(
                    int(value.get("view") or 0)
                    for day, value in daily_rows.items()
                    if day <= report_date
                )
                trends_by_code[product_code][report_date]["download"] = sum(
                    int(value.get("download") or 0)
                    for day, value in daily_rows.items()
                    if day <= report_date
                )

        overview = []
        for report_date in report_dates:
            overview.append(trend_row(
                report_date,
                sum(trends_by_code[code][report_date]["view"] for code in codes),
                sum(trends_by_code[code][report_date]["download"] for code in codes),
            ))
        return {
            "overview": overview,
            "products": {
                code: [trends_by_code[code][report_date] for report_date in report_dates]
                for code in codes
            },
        }

    if snapshot_rows:
        snapshots_by_post = {}
        for row in snapshot_rows:
            item = row_dict(row)
            key = (str(item.get("product_code") or "").strip().upper(), str(item.get("post_id") or ""))
            snapshots_by_post.setdefault(key, []).append((
                str(item.get("snapshot_date") or "")[:10],
                int(item.get("view_count") or 0),
            ))

        for (product_code, _post_id), snapshots in snapshots_by_post.items():
            if product_code not in trends_by_code:
                continue
            latest_view = 0
            index = 0
            for report_date in report_dates:
                while index < len(snapshots) and snapshots[index][0] <= report_date:
                    latest_view = snapshots[index][1]
                    index += 1
                trends_by_code[product_code][report_date]["view"] += latest_view

    overview = []
    for report_date in report_dates:
        overview.append(trend_row(
            report_date,
            sum(trends_by_code[code][report_date]["view"] for code in codes),
            sum(trends_by_code[code][report_date]["download"] for code in codes),
        ))
    return {
        "overview": overview,
        "products": {
            code: [trends_by_code[code][report_date] for report_date in report_dates]
            for code in codes
        },
    }
