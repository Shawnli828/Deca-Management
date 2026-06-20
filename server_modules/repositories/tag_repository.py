def fetch_account_tag_rows(account_ids, *, connect_db, init_relational_schema, placeholder):
    ids = [str(item or "").strip() for item in account_ids if str(item or "").strip()]
    if not ids:
        return []
    placeholders = ",".join([placeholder] * len(ids))
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"SELECT account_id, tag FROM account_tags WHERE account_id IN ({placeholders}) ORDER BY tag",
            tuple(ids),
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_product_tag_values(product_code, *, connect_db, init_relational_schema, placeholder):
    with connect_db() as conn:
        init_relational_schema(conn)
        option_rows = conn.execute(
            f"SELECT tag FROM product_tags WHERE product_code = {placeholder}",
            (product_code,),
        ).fetchall()
        used_rows = conn.execute(
            f"""
            SELECT DISTINCT tag.tag
            FROM account_tags tag
            JOIN accounts acc ON acc.id = tag.account_id
            JOIN product_market_channels pmc ON pmc.id = acc.product_market_channel_id
            JOIN product_markets pm ON pm.id = pmc.product_market_id
            JOIN products p ON p.id = pm.product_id
            WHERE p.code = {placeholder}
            """,
            (product_code,),
        ).fetchall()
    return [dict(row).get("tag") for row in [*option_rows, *used_rows]]
