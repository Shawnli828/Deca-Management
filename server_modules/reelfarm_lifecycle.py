from server_modules.db_core import connect_db, db_placeholder
from server_modules.reelfarm_client import reelfarm_product_automation_ids
from server_modules.reelfarm_utils import reelfarm_expected_automation_condition
from server_modules.schema import init_relational_schema


def active_tiktok_automation_account_ids(conn, account_ids):
    ids = [str(item or "").strip() for item in (account_ids or []) if str(item or "").strip()]
    if not ids:
        return set()
    placeholder = db_placeholder()
    placeholders = ",".join([placeholder] * len(ids))
    rows = conn.execute(
        f"""
        SELECT DISTINCT acc.id AS account_id
        FROM accounts acc
        JOIN product_market_channels pmc ON pmc.id = acc.product_market_channel_id
        JOIN channels ch ON ch.id = pmc.channel_id
        JOIN automations a ON a.account_id = acc.id
        WHERE acc.id IN ({placeholders})
          AND UPPER(COALESCE(ch.code, '')) = {placeholder}
          AND {reelfarm_expected_automation_condition("a")}
        """,
        tuple(ids + ["TIKTOK"]),
    ).fetchall()
    return {str(dict(row).get("account_id") or "") for row in rows}


def mark_missing_reelfarm_automations(conn, product_market_channel_id, seen_reelfarm_ids, synced_at):
    seen = sorted({str(item or "").strip() for item in (seen_reelfarm_ids or []) if str(item or "").strip()})
    placeholder = db_placeholder()
    if seen:
        seen_placeholders = ", ".join([placeholder] * len(seen))
        conn.execute(
            f"""
            UPDATE automations
            SET sync_status = 'deleted',
                deleted_at = COALESCE(NULLIF(deleted_at, ''), {placeholder}),
                synced_at = {placeholder}
            WHERE product_market_channel_id = {placeholder}
              AND reelfarm_automation_id NOT IN ({seen_placeholders})
              AND LOWER(COALESCE(sync_status, 'present')) <> 'deleted'
            """,
            (synced_at, synced_at, product_market_channel_id, *seen),
        )
        return

    conn.execute(
        f"""
        UPDATE automations
        SET sync_status = 'deleted',
            deleted_at = COALESCE(NULLIF(deleted_at, ''), {placeholder}),
            synced_at = {placeholder}
        WHERE product_market_channel_id = {placeholder}
          AND LOWER(COALESCE(sync_status, 'present')) <> 'deleted'
        """,
        (synced_at, synced_at, product_market_channel_id),
    )


def mark_missing_reelfarm_product_automations(conn, product_code, seen_reelfarm_ids, synced_at):
    product_code = str(product_code or "").strip().upper()
    if not product_code:
        return 0

    seen = sorted({str(item or "").strip() for item in (seen_reelfarm_ids or []) if str(item or "").strip()})
    placeholder = db_placeholder()
    seen_filter = ""
    params = [synced_at, synced_at, product_code]
    if seen:
        seen_placeholders = ", ".join([placeholder] * len(seen))
        seen_filter = f"AND a.reelfarm_automation_id NOT IN ({seen_placeholders})"
        params.extend(seen)

    cursor = conn.execute(
        f"""
        UPDATE automations
        SET sync_status = 'deleted',
            deleted_at = COALESCE(NULLIF(deleted_at, ''), {placeholder}),
            synced_at = {placeholder}
        WHERE id IN (
            SELECT a.id
            FROM automations a
            JOIN product_market_channels pmc ON pmc.id = a.product_market_channel_id
            JOIN product_markets pm ON pm.id = pmc.product_market_id
            JOIN products p ON p.id = pm.product_id
            JOIN channels ch ON ch.id = pmc.channel_id
            WHERE p.code = {placeholder}
              AND ch.code = 'TIKTOK'
              AND LOWER(COALESCE(a.sync_status, 'present')) <> 'deleted'
              {seen_filter}
        )
        """,
        tuple(params),
    )
    return max(int(cursor.rowcount or 0), 0)


def cleanup_reelfarm_product_from_latest_automations(product_code, automations, synced_at):
    seen_ids = reelfarm_product_automation_ids(automations, product_code)
    if not seen_ids:
        return {
            "product_code": str(product_code or "").strip().upper(),
            "latest_reelfarm_automation_count": 0,
            "marked_deleted_count": 0,
            "skipped": True,
            "reason": "No matching ReelFarm automation titles found for product code.",
        }

    with connect_db() as conn:
        init_relational_schema(conn)
        deleted_count = mark_missing_reelfarm_product_automations(conn, product_code, seen_ids, synced_at)
        conn.commit()
    return {
        "product_code": str(product_code or "").strip().upper(),
        "latest_reelfarm_automation_count": len(seen_ids),
        "marked_deleted_count": deleted_count,
    }
