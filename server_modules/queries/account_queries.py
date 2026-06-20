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
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            WITH account_base AS (
                SELECT
                    p.id AS product_id,
                    p.code AS product_code,
                    p.name AS product_name,
                    m.id AS country_id,
                    m.id AS market_id,
                    m.code AS country_code,
                    m.code AS market_code,
                    m.name AS country_name,
                    pmc.id AS product_market_channel_id,
                    acc.id AS account_id,
                    acc.reelfarm_account_id,
                    acc.username,
                    acc.display_name,
                    acc.avatar_url,
                    CASE
                        WHEN SUM(CASE WHEN LOWER(COALESCE(a.status, '')) = 'active' THEN 1 ELSE 0 END) > 0 THEN 'active'
                        ELSE COALESCE(MAX(NULLIF(a.status, '')), '')
                    END AS status,
                    COUNT(DISTINCT a.id) AS automation_count,
                    MAX(a.name) AS automation_name,
                    {automation_names_sql} AS automation_names,
                    MAX(a.post_mode) AS post_mode,
                    CASE
                        WHEN SUM(CASE WHEN a.publish_method = 'manual' THEN 1 ELSE 0 END) > 0 THEN 'manual'
                        WHEN SUM(CASE WHEN a.publish_method = 'rpa' THEN 1 ELSE 0 END) > 0 THEN 'rpa'
                        ELSE 'api'
                    END AS publish_method,
                    {expected_account_sql} AS expected_account_count,
                    MAX(a.synced_at) AS base_synced_at
                FROM products p
                JOIN product_markets pm ON pm.product_id = p.id
                JOIN markets m ON m.id = pm.market_id
                JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
                JOIN channels ch ON ch.id = pmc.channel_id
                LEFT JOIN automations a ON a.product_market_channel_id = pmc.id
                LEFT JOIN accounts acc ON acc.id = a.account_id
                WHERE {account_where_sql}
                GROUP BY
                    p.id,
                    p.code,
                    p.name,
                    m.id,
                    m.code,
                    m.name,
                    pmc.id,
                    acc.id,
                    acc.reelfarm_account_id,
                    acc.username,
                    acc.display_name,
                    acc.avatar_url
            ),
            metrics AS (
                SELECT
                    acc.id AS account_id,
                    COUNT(DISTINCT mat.id) AS material_count,
                    COUNT(DISTINCT post.id) AS post_count,
                    CASE WHEN COUNT(DISTINCT post.id) > 0 THEN 1 ELSE 0 END AS posted_account_count,
                    COALESCE(SUM(post.view_count), 0) AS total_views,
                    COALESCE(SUM(post.like_count), 0) AS total_likes,
                    COALESCE(SUM(post.comment_count), 0) AS total_comments,
                    COALESCE(SUM(post.share_count), 0) AS total_shares,
                    COALESCE(SUM(post.bookmark_count), 0) AS total_bookmarks,
                    MAX(post.published_at) AS latest_post_at,
                    MAX(COALESCE(post.synced_at, mat.synced_at, a.synced_at)) AS metric_synced_at
                {relational_base_from()}
                WHERE {metric_where_sql}
                GROUP BY acc.id
            )
            SELECT
                account_base.product_id,
                account_base.product_code,
                account_base.product_name,
                account_base.country_id,
                account_base.market_id,
                account_base.country_code,
                account_base.market_code,
                account_base.country_name,
                account_base.product_market_channel_id,
                account_base.account_id,
                account_base.reelfarm_account_id,
                account_base.username,
                account_base.display_name,
                account_base.avatar_url,
                account_base.status,
                account_base.automation_count,
                account_base.automation_name,
                account_base.automation_names,
                account_base.post_mode,
                account_base.publish_method,
                COALESCE(metrics.material_count, 0) AS material_count,
                COALESCE(metrics.post_count, 0) AS post_count,
                COALESCE(metrics.posted_account_count, 0) AS posted_account_count,
                account_base.expected_account_count,
                COALESCE(metrics.total_views, 0) AS total_views,
                COALESCE(metrics.total_likes, 0) AS total_likes,
                COALESCE(metrics.total_comments, 0) AS total_comments,
                COALESCE(metrics.total_shares, 0) AS total_shares,
                COALESCE(metrics.total_bookmarks, 0) AS total_bookmarks,
                COALESCE(metrics.latest_post_at, '') AS latest_post_at,
                COALESCE(metrics.metric_synced_at, account_base.base_synced_at, '') AS last_synced_at
            FROM account_base
            LEFT JOIN metrics ON metrics.account_id = account_base.account_id
            ORDER BY total_views DESC, post_count DESC
            """,
            tuple(account_params + metric_params),
        ).fetchall()
    return [normalize_reelfarm_account_row(row_dict(row)) for row in rows]
