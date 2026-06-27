from datetime import datetime, timezone

from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema
from server_modules.common import stable_id
from server_modules.data_query_helpers import row_dict
from server_modules.db_core import upsert_row as upsert_row_impl


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def fetch_product_country_automation_counts():
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                p.id AS product_id,
                p.name AS product_name,
                p.code AS product_code,
                COALESCE(p.owner_type, '') AS owner_type,
                p.logo_url AS logo_url,
                m.id AS country_id,
                m.name AS country_name,
                m.code AS country_code,
                COUNT(DISTINCT CASE
                    WHEN LOWER(COALESCE(a.status, '')) = 'active'
                     AND COALESCE(a.deleted_at, '') = ''
                     AND COALESCE(a.source, 'reelfarm') = 'reelfarm'
                    THEN a.id
                END) AS active_count
            FROM product_market_channels pmc
            JOIN product_markets pm ON pm.id = pmc.product_market_id
            JOIN products p ON p.id = pm.product_id
            JOIN markets m ON m.id = pm.market_id
            JOIN channels ch ON ch.id = pmc.channel_id
            LEFT JOIN automations a ON a.product_market_channel_id = pmc.id
            WHERE ch.code = {placeholder}
              AND COALESCE(p.owner_type, '') <> {placeholder}
            GROUP BY p.id, p.name, p.code, p.owner_type, p.logo_url, m.id, m.name, m.code
            ORDER BY p.name, m.name
            """,
            ("TIKTOK", "乙方"),
        ).fetchall()
    return [row_dict(row) for row in rows]


def fetch_targets():
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            """
            SELECT id, product_code, country_code, target_count, note, created_at, updated_at
            FROM automation_coverage_targets
            ORDER BY product_code, country_code
            """
        ).fetchall()
    return [row_dict(row) for row in rows]


def fetch_warmup_batches(include_closed=False):
    placeholder = db_placeholder()
    params = []
    where = ""
    if not include_closed:
        where = f"WHERE status NOT IN ({placeholder}, {placeholder})"
        params = ["activated", "cancelled"]
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                id,
                product_code,
                country_code,
                batch_name,
                account_count,
                warmup_start_date,
                warmup_days,
                warmup_end_date,
                status,
                note,
                created_at,
                updated_at
            FROM automation_warmup_batches
            {where}
            ORDER BY warmup_end_date, created_at
            """,
            tuple(params),
        ).fetchall()
    return [row_dict(row) for row in rows]


def fetch_warmup_batch(batch_id):
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"""
            SELECT
                id,
                product_code,
                country_code,
                batch_name,
                account_count,
                warmup_start_date,
                warmup_days,
                warmup_end_date,
                status,
                note,
                created_at,
                updated_at
            FROM automation_warmup_batches
            WHERE id = {placeholder}
            """,
            (str(batch_id or "").strip(),),
        ).fetchone()
    return row_dict(row) if row else None


def upsert_target(product_code, country_code, target_count, note=""):
    timestamp = now_iso()
    product_code = str(product_code or "").strip().upper()
    country_code = str(country_code or "").strip().upper()
    record = {
        "id": stable_id("automation_coverage_target", product_code, country_code),
        "product_code": product_code,
        "country_code": country_code,
        "target_count": int(target_count or 0),
        "note": str(note or "").strip(),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(
            conn,
            "automation_coverage_targets",
            record,
            ["product_code", "country_code"],
            ["target_count", "note", "updated_at"],
        )
        conn.commit()
    return record


def insert_warmup_batch(record):
    timestamp = now_iso()
    clean = {
        "id": record.get("id") or stable_id(
            "automation_warmup_batch",
            record.get("product_code"),
            record.get("country_code"),
            record.get("batch_name"),
            timestamp,
        ),
        "product_code": str(record.get("product_code") or "").strip().upper(),
        "country_code": str(record.get("country_code") or "").strip().upper(),
        "batch_name": str(record.get("batch_name") or "").strip(),
        "account_count": int(record.get("account_count") or 0),
        "warmup_start_date": str(record.get("warmup_start_date") or "").strip(),
        "warmup_days": int(record.get("warmup_days") or 7),
        "warmup_end_date": str(record.get("warmup_end_date") or "").strip(),
        "status": str(record.get("status") or "warming").strip() or "warming",
        "note": str(record.get("note") or "").strip(),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(conn, "automation_warmup_batches", clean, ["id"])
        conn.commit()
    return clean


def update_warmup_batch(batch_id, updates):
    allowed = {"batch_name", "account_count", "warmup_start_date", "warmup_days", "warmup_end_date", "status", "note"}
    clean_updates = {key: value for key, value in updates.items() if key in allowed}
    if not clean_updates:
        return None

    clean_updates["updated_at"] = now_iso()
    placeholder = db_placeholder()
    set_clause = ", ".join([f"{key} = {placeholder}" for key in clean_updates])
    params = [*clean_updates.values(), str(batch_id or "").strip()]
    with connect_db() as conn:
        init_relational_schema(conn)
        conn.execute(
            f"UPDATE automation_warmup_batches SET {set_clause} WHERE id = {placeholder}",
            tuple(params),
        )
        row = conn.execute(
            f"""
            SELECT
                id,
                product_code,
                country_code,
                batch_name,
                account_count,
                warmup_start_date,
                warmup_days,
                warmup_end_date,
                status,
                note,
                created_at,
                updated_at
            FROM automation_warmup_batches
            WHERE id = {placeholder}
            """,
            (str(batch_id or "").strip(),),
        ).fetchone()
        conn.commit()
    return row_dict(row) if row else None
