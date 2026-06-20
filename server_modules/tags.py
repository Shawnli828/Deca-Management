import re
from datetime import datetime, timezone

from server_modules.common import stable_id
from server_modules.repositories.tag_repository import fetch_account_tag_rows, fetch_product_tag_values


def clean_tag(value):
    tag = re.sub(r"\s+", " ", str(value or "")).strip()
    return tag[:40]


def existing_tag_value(conn, table, scope_column, scope_value, tag, *, placeholder):
    row = conn.execute(
        f"""
        SELECT tag
        FROM {table}
        WHERE {scope_column} = {placeholder}
          AND LOWER(tag) = LOWER({placeholder})
        LIMIT 1
        """,
        (scope_value, tag),
    ).fetchone()
    data = dict(row) if row else {}
    return data.get("tag") or tag


def account_tags_payload(account_ids, *, connect_db, init_relational_schema, placeholder):
    ids = [str(item or "").strip() for item in account_ids if str(item or "").strip()]
    if not ids:
        return {"ok": True, "tags": {}}
    tags = {}
    for data in fetch_account_tag_rows(
        ids,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=placeholder,
    ):
        tags.setdefault(data.get("account_id"), []).append(data.get("tag"))
    return {"ok": True, "tags": tags}


def product_tags_payload(product_code, *, connect_db, init_relational_schema, placeholder):
    product_code = str(product_code or "").strip().upper()
    if not product_code:
        raise ValueError("product_code is required.")
    tags = sorted({
        clean_tag(tag)
        for tag in fetch_product_tag_values(
            product_code,
            connect_db=connect_db,
            init_relational_schema=init_relational_schema,
            placeholder=placeholder,
        )
        if clean_tag(tag)
    }, key=lambda value: value.lower())
    return {"ok": True, "product_code": product_code, "tags": tags}


def create_product_tag(
    product_code,
    tag,
    *,
    connect_db,
    init_relational_schema,
    upsert_row,
    placeholder,
):
    product_code = str(product_code or "").strip().upper()
    tag = clean_tag(tag)
    if not product_code or not tag:
        raise ValueError("product_code and tag are required.")
    now = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        init_relational_schema(conn)
        tag = existing_tag_value(conn, "product_tags", "product_code", product_code, tag, placeholder=placeholder)
        upsert_row(
            conn,
            "product_tags",
            {"id": stable_id("product_tag", product_code, tag.lower()), "product_code": product_code, "tag": tag, "created_at": now},
            ["id"],
        )
        conn.commit()
    return product_tags_payload(
        product_code,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=placeholder,
    )


def delete_product_tag(
    product_code,
    tag,
    remove_assignments=True,
    *,
    connect_db,
    init_relational_schema,
    placeholder,
):
    product_code = str(product_code or "").strip().upper()
    tag = clean_tag(tag)
    if not product_code or not tag:
        raise ValueError("product_code and tag are required.")

    removed_assignments = 0
    with connect_db() as conn:
        init_relational_schema(conn)
        canonical_tag = existing_tag_value(conn, "product_tags", "product_code", product_code, tag, placeholder=placeholder)
        conn.execute(
            f"DELETE FROM product_tags WHERE product_code = {placeholder} AND LOWER(tag) = LOWER({placeholder})",
            (product_code, canonical_tag),
        )
        if remove_assignments:
            account_rows = conn.execute(
                f"""
                SELECT acc.id
                FROM accounts acc
                JOIN product_market_channels pmc ON pmc.id = acc.product_market_channel_id
                JOIN product_markets pm ON pm.id = pmc.product_market_id
                JOIN products p ON p.id = pm.product_id
                WHERE p.code = {placeholder}
                """,
                (product_code,),
            ).fetchall()
            account_ids = [dict(row).get("id") for row in account_rows if dict(row).get("id")]
            if account_ids:
                placeholders = ", ".join([placeholder] * len(account_ids))
                cursor = conn.execute(
                    f"""
                    DELETE FROM account_tags
                    WHERE LOWER(tag) = LOWER({placeholder})
                      AND account_id IN ({placeholders})
                    """,
                    (canonical_tag, *account_ids),
                )
                removed_assignments = cursor.rowcount or 0
        conn.commit()

    payload = product_tags_payload(
        product_code,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=placeholder,
    )
    payload["deleted_tag"] = canonical_tag
    payload["removed_account_tags"] = removed_assignments
    return payload


def add_account_tag(
    account_id,
    tag,
    *,
    connect_db,
    init_relational_schema,
    upsert_row,
    placeholder,
):
    account_id = str(account_id or "").strip()
    tag = clean_tag(tag)
    if not account_id or not tag:
        raise ValueError("account_id and tag are required.")
    now = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        init_relational_schema(conn)
        tag = existing_tag_value(conn, "account_tags", "account_id", account_id, tag, placeholder=placeholder)
        upsert_row(
            conn,
            "account_tags",
            {"id": stable_id("account_tag", account_id, tag.lower()), "account_id": account_id, "tag": tag, "created_at": now},
            ["id"],
        )
        conn.commit()
    return {"ok": True, "account_id": account_id, "tag": tag}


def delete_account_tag(account_id, tag, *, connect_db, init_relational_schema, placeholder):
    account_id = str(account_id or "").strip()
    tag = clean_tag(tag)
    if not account_id or not tag:
        raise ValueError("account_id and tag are required.")
    with connect_db() as conn:
        init_relational_schema(conn)
        conn.execute(f"DELETE FROM account_tags WHERE account_id = {placeholder} AND tag = {placeholder}", (account_id, tag))
        conn.commit()
    return {"ok": True, "account_id": account_id, "tag": tag}
