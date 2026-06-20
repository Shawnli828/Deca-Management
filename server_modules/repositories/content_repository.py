def fetch_post_rows(
    *,
    where_sql,
    params,
    order_sql,
    limit,
    offset,
    placeholder,
    connect_db,
    init_relational_schema,
    relational_base_from,
    detailed_select,
    row_dict,
    hydrate_rows=None,
):
    with connect_db() as conn:
        init_relational_schema(conn)
        total_row = conn.execute(
            f"""
            SELECT COUNT(DISTINCT post.id) AS total
            {relational_base_from()}
            WHERE {where_sql} AND post.id IS NOT NULL
            """,
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            f"""
            SELECT {detailed_select()}
            {relational_base_from()}
            WHERE {where_sql} AND post.id IS NOT NULL
            ORDER BY {order_sql}
            LIMIT {placeholder} OFFSET {placeholder}
            """,
            tuple(params + [limit, offset]),
        ).fetchall()
        row_data = [row_dict(row) for row in rows]
        if hydrate_rows:
            row_data = hydrate_rows(conn, row_data)
    return row_data, row_dict(total_row).get("total", 0)


def fetch_material_rows(
    *,
    where_sql,
    params,
    limit,
    offset,
    placeholder,
    connect_db,
    init_relational_schema,
    relational_base_from,
    detailed_select,
    row_dict,
):
    with connect_db() as conn:
        init_relational_schema(conn)
        total_row = conn.execute(
            f"""
            SELECT COUNT(DISTINCT mat.id) AS total
            {relational_base_from()}
            WHERE {where_sql} AND mat.id IS NOT NULL
            """,
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            f"""
            SELECT {detailed_select()}
            {relational_base_from()}
            WHERE {where_sql} AND mat.id IS NOT NULL
            ORDER BY mat.created_at DESC, post.published_at DESC
            LIMIT {placeholder} OFFSET {placeholder}
            """,
            tuple(params + [limit, offset]),
        ).fetchall()
    return rows, row_dict(total_row).get("total", 0)
