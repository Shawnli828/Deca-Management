import json
import sqlite3
import ssl
from datetime import datetime, timezone
from pathlib import Path


def using_postgres(database_url):
    return bool(database_url)


def db_placeholder(database_url):
    return "%s" if using_postgres(database_url) else "?"


def make_ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        for candidate in (
            "/etc/ssl/cert.pem",
            "/opt/homebrew/etc/openssl@3/cert.pem",
            "/usr/local/etc/openssl@3/cert.pem",
        ):
            if Path(candidate).is_file():
                return ssl.create_default_context(cafile=candidate)

    return ssl.create_default_context()


def connect_db(database_url, db_path):
    if using_postgres(database_url):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError(
                "DATABASE_URL is set, but psycopg is not installed. "
                "Run: pip install -r requirements.txt"
            ) from error

        return psycopg.connect(database_url, row_factory=dict_row)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_app_state_db(connect_db_fn, init_relational_schema_fn, placeholder, state_key, initial_data_fn, save_data_fn):
    with connect_db_fn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        init_relational_schema_fn(conn)
        row = conn.execute(
            f"SELECT key FROM app_state WHERE key = {placeholder}",
            (state_key,),
        ).fetchone()
        if row is None:
            save_data_fn(initial_data_fn(), conn)
        conn.commit()


def save_app_value(key, value, connect_db_fn, placeholder, conn=None):
    payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat()
    owns_connection = conn is None
    if owns_connection:
        conn = connect_db_fn()
    try:
        conn.execute(
            f"""
            INSERT INTO app_state (key, value, updated_at)
            VALUES ({placeholder}, {placeholder}, {placeholder})
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, payload, now),
        )
        conn.commit()
    finally:
        if owns_connection:
            conn.close()


def load_app_value(key, init_db_fn, connect_db_fn, placeholder):
    init_db_fn()
    with connect_db_fn() as conn:
        row = conn.execute(
            f"SELECT value FROM app_state WHERE key = {placeholder}",
            (key,),
        ).fetchone()
    return row["value"] if row else ""


def delete_app_value(key, init_db_fn, connect_db_fn, placeholder):
    init_db_fn()
    with connect_db_fn() as conn:
        conn.execute(f"DELETE FROM app_state WHERE key = {placeholder}", (key,))
        conn.commit()


def upsert_row(conn, table, values, conflict_cols, placeholder, update_cols=None):
    columns = list(values.keys())
    placeholders = ", ".join([placeholder] * len(columns))
    column_sql = ", ".join(columns)
    conflict_sql = ", ".join(conflict_cols)
    if update_cols is None:
        update_cols = [column for column in columns if column not in conflict_cols]
    if update_cols:
        update_sql = ", ".join(f"{column} = excluded.{column}" for column in update_cols)
        conflict_action = f"DO UPDATE SET {update_sql}"
    else:
        conflict_action = "DO NOTHING"
    conn.execute(
        f"""
        INSERT INTO {table} ({column_sql})
        VALUES ({placeholders})
        ON CONFLICT({conflict_sql}) {conflict_action}
        """,
        tuple(values[column] for column in columns),
    )
