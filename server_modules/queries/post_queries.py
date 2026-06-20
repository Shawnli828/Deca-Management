def query_posts(
    query,
    top_metric="",
    *,
    query_limit_offset,
    common_where,
    db_placeholder,
    connect_db,
    init_relational_schema,
    relational_base_from,
    detailed_select,
    row_dict,
    query_value,
    data_source_channel_code,
    hydrate_museon_images_for_rows,
    detailed_row,
    pagination_payload,
):
    max_limit = 100 if top_metric else 500
    limit, offset = query_limit_offset(query, max_limit=max_limit)
    where_sql, params = common_where(query)
    order_sql = f"post.{top_metric} DESC, post.published_at DESC" if top_metric else "post.published_at DESC"
    placeholder = db_placeholder()
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
        if (
            query_value(query, "resource").lower() == "account_posts"
            and data_source_channel_code(query_value(query, "source")) == "MUSEON_CLONE"
        ):
            row_data = hydrate_museon_images_for_rows(conn, row_data)
    return [detailed_row(row) for row in row_data], pagination_payload(limit, offset, row_data, row_dict(total_row).get("total", 0))


def query_materials(
    query,
    *,
    query_limit_offset,
    common_where,
    db_placeholder,
    connect_db,
    init_relational_schema,
    relational_base_from,
    detailed_select,
    detailed_row,
    pagination_payload,
    row_dict,
):
    limit, offset = query_limit_offset(query)
    where_sql, params = common_where(query)
    placeholder = db_placeholder()
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
    return [detailed_row(row) for row in rows], pagination_payload(limit, offset, rows, row_dict(total_row).get("total", 0))
