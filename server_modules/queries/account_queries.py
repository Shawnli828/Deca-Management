from server_modules.repositories.account_repository import fetch_reelfarm_account_rows


def query_reelfarm_accounts(
    query,
    *,
    data_source_channel_code,
    query_value,
    query_days_window,
    post_datetime_bound,
    db_placeholder,
    common_where,
    reelfarm_dashboard_automation_condition,
    reelfarm_expected_automation_condition,
    using_postgres,
    connect_db,
    init_relational_schema,
    relational_base_from,
    row_dict,
    normalize_reelfarm_account_row,
):
    channel_code = data_source_channel_code(query_value(query, "source"))
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if not date_from and not date_to:
        date_from, date_to = query_days_window(query)
    metric_date_column = "mat.created_at" if channel_code == "TIKTOK" else "post.published_at"
    placeholder = db_placeholder()

    account_where = ["ch.code = " + placeholder]
    account_params = [channel_code]
    product_code = query_value(query, "product_code").upper()
    market_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    account_id = query_value(query, "account_id")
    automation_id = query_value(query, "automation_id")
    if product_code:
        account_where.append("p.code = " + placeholder)
        account_params.append(product_code)
    if market_code:
        account_where.append("m.code = " + placeholder)
        account_params.append(market_code)
    if account_id:
        account_where.append(f"(acc.id = {placeholder} OR acc.reelfarm_account_id = {placeholder} OR acc.username = {placeholder})")
        account_params.extend([account_id, account_id, account_id.lstrip("@")])
    if automation_id:
        account_where.append(f"(a.id = {placeholder} OR a.reelfarm_automation_id = {placeholder})")
        account_params.extend([automation_id, automation_id])
    if channel_code == "TIKTOK":
        account_where.append(reelfarm_dashboard_automation_condition("a"))
    account_where.append("acc.id IS NOT NULL")
    account_where_sql = " AND ".join(account_where)

    metric_where_sql, metric_params = common_where(query, include_post_dates=False)
    metric_where = [metric_where_sql, "acc.id IS NOT NULL", "post.id IS NOT NULL"]
    if channel_code == "TIKTOK":
        metric_where.append(reelfarm_expected_automation_condition("a"))
    if date_from:
        metric_where.append(f"{metric_date_column} >= {placeholder}")
        metric_params.append(post_datetime_bound(date_from))
    if date_to:
        metric_where.append(f"{metric_date_column} <= {placeholder}")
        metric_params.append(post_datetime_bound(date_to, end=True))
    metric_where_sql = " AND ".join(metric_where)

    automation_names_sql = (
        "STRING_AGG(DISTINCT a.name, ' | ')"
        if using_postgres()
        else "GROUP_CONCAT(DISTINCT a.name)"
    )
    expected_account_sql = (
        f"CASE WHEN SUM(CASE WHEN {reelfarm_expected_automation_condition('a')} THEN 1 ELSE 0 END) > 0 THEN 1 ELSE 0 END"
        if channel_code == "TIKTOK"
        else "1"
    )
    rows = fetch_reelfarm_account_rows(
        account_where_sql=account_where_sql,
        account_params=account_params,
        metric_where_sql=metric_where_sql,
        metric_params=metric_params,
        automation_names_sql=automation_names_sql,
        expected_account_sql=expected_account_sql,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        relational_base_from=relational_base_from,
        row_dict=row_dict,
    )
    return [normalize_reelfarm_account_row(row) for row in rows]
