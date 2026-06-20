from server_modules.repositories.content_repository import fetch_material_rows, fetch_post_rows


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
    hydrate_rows = None
    if (
        query_value(query, "resource").lower() == "account_posts"
        and data_source_channel_code(query_value(query, "source")) == "MUSEON_CLONE"
    ):
        hydrate_rows = hydrate_museon_images_for_rows
    row_data, total = fetch_post_rows(
        where_sql=where_sql,
        params=params,
        order_sql=order_sql,
        limit=limit,
        offset=offset,
        placeholder=placeholder,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        relational_base_from=relational_base_from,
        detailed_select=detailed_select,
        row_dict=row_dict,
        hydrate_rows=hydrate_rows,
    )
    return [detailed_row(row) for row in row_data], pagination_payload(limit, offset, row_data, total)


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
    rows, total = fetch_material_rows(
        where_sql=where_sql,
        params=params,
        limit=limit,
        offset=offset,
        placeholder=placeholder,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        relational_base_from=relational_base_from,
        detailed_select=detailed_select,
        row_dict=row_dict,
    )
    return [detailed_row(row) for row in rows], pagination_payload(limit, offset, rows, total)
