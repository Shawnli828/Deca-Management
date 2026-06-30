from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema
from server_modules.data_query_helpers import relational_base_from, row_dict
from server_modules.db_core import upsert_row as upsert_row_impl


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


def list_ab_tests():
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM ab_tests
            ORDER BY start_date DESC, created_at DESC
            """
        ).fetchall()
    return [row_dict(row) for row in rows]


def get_ab_test(test_id):
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"SELECT * FROM ab_tests WHERE id = {placeholder}",
            (test_id,),
        ).fetchone()
    return row_dict(row)


def create_ab_test(record):
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(conn, "ab_tests", record, ["id"])
        conn.commit()
    return get_ab_test(record["id"])


def update_ab_test(test_id, updates):
    if not updates:
        return get_ab_test(test_id)
    allowed = {
        "name",
        "product_code",
        "country_code",
        "start_date",
        "duration_days",
        "variable",
        "hypothesis",
        "note",
        "conclusion",
        "conclusion_status",
        "updated_at",
    }
    clean = {key: value for key, value in updates.items() if key in allowed}
    if not clean:
        return get_ab_test(test_id)

    placeholder = db_placeholder()
    assignments = ", ".join(f"{key} = {placeholder}" for key in clean)
    values = list(clean.values()) + [test_id]
    with connect_db() as conn:
        init_relational_schema(conn)
        conn.execute(
            f"UPDATE ab_tests SET {assignments} WHERE id = {placeholder}",
            tuple(values),
        )
        conn.commit()
    return get_ab_test(test_id)


def delete_ab_test(test_id):
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        conn.execute(f"DELETE FROM ab_tests WHERE id = {placeholder}", (test_id,))
        conn.commit()
    return {"id": test_id}


def country_business_material_rows(product_code, country_code, utc_start, utc_end):
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
              AND m.code = {placeholder}
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
                str(country_code or "").upper(),
                utc_start.isoformat(),
                utc_end.isoformat(),
                utc_start.isoformat(),
                utc_end.isoformat(),
            ),
        ).fetchall()
    return [row_dict(row) for row in rows]
