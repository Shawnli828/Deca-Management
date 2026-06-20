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
