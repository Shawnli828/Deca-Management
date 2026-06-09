#!/usr/bin/env python3
import json
import base64
import hashlib
import hmac
import mimetypes
import os
import re
import secrets
import ssl
import sqlite3
import socket
import time
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "management_table.sqlite3"
DATABASE_URL = (
    os.environ.get("DATABASE_URL", "")
    or os.environ.get("POSTGRES_URL", "")
    or os.environ.get("POSTGRES_PRISMA_URL", "")
    or os.environ.get("POSTGRES_URL_NON_POOLING", "")
).strip()
STATE_KEY = "product_distribution"
REELFARM_API_KEY = "reel_farm_api_key"
PUBLISH_CHECK_STATE_KEY = "publish_check_state"
EXTERNAL_API_KEYS_KEY = "external_api_keys"
ZERO_PLAY_ISSUE = "0播警告"
ZERO_PLAY_VIEW_THRESHOLD = 0
ZERO_PLAY_POST_LIMIT = 2
BUSINESS_TIMEZONE = timezone(timedelta(hours=8))
REELFARM_BASE_URL = "https://reel.farm/api/v1"
MUSEON_BASE_URL = os.environ.get("MUSEON_BASE_URL", "https://api.museon.ai/external/api/v1").strip().rstrip("/")
MUSEON_API_KEY = os.environ.get("MUSEON_API_KEY", "").strip()
MUSEON_WORKSPACE_ID = os.environ.get("MUSEON_WORKSPACE_ID", "b5e25f84-b3ed-484b-b467-901a4afcd9c6").strip()
MUSEON_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
MIXPANEL_SERVICE_ACCOUNT_USERNAME = os.environ.get("MIXPANEL_SERVICE_ACCOUNT_USERNAME", "").strip()
MIXPANEL_SERVICE_ACCOUNT_SECRET = os.environ.get("MIXPANEL_SERVICE_ACCOUNT_SECRET", "").strip()
MIXPANEL_PROJECT_ID = os.environ.get("MIXPANEL_PROJECT_ID", "").strip()
MIXPANEL_REGION = os.environ.get("MIXPANEL_REGION", "standard").strip().lower()
MIXPANEL_DOWNLOAD_EVENT = os.environ.get("MIXPANEL_DOWNLOAD_EVENT", "Download").strip()
MIXPANEL_ONBOARDING_EVENT = os.environ.get("MIXPANEL_ONBOARDING_EVENT", "Onboarding Step Viewed").strip()
REPORT_TIMEZONE_NAME = os.environ.get("REPORT_TIMEZONE", "Asia/Shanghai").strip()
MIXPANEL_TIMEZONE_NAME = os.environ.get("MIXPANEL_TIMEZONE", "America/Los_Angeles").strip()
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
FEISHU_WEBHOOK_SECRET = os.environ.get("FEISHU_WEBHOOK_SECRET", "").strip()
SEED_DATA_PATH = BASE_DIR / "seed_data.json"
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Deca888").strip()
ADMIN_PASSWORD_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    "baacd133a9696faa0333b9a7a8d3f0e3b560ef781a494d017d0d2ea19d46c0b1",
).strip()
SESSION_SECRET = os.environ.get("SESSION_SECRET", ADMIN_PASSWORD_HASH).strip()
SESSION_COOKIE = "deca_growth_session"
SESSION_TTL_SECONDS = 60 * 60 * 12
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
COUNTRY_CODES = {
    "United States": "US",
    "United Kingdom": "UK",
    "Japan": "JP",
    "Germany": "DE",
    "Brazil": "BR",
    "India": "IN",
    "China": "CN",
    "France": "FR",
    "Italy": "IT",
    "Canada": "CA",
    "Australia": "AU",
    "South Korea": "KR",
}


def using_postgres():
    return bool(DATABASE_URL)


def db_placeholder():
    return "%s" if using_postgres() else "?"


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


def generate_id():
    return uuid.uuid4().hex[:9]


def stable_id(namespace, *parts):
    value = "|".join(str(part or "").strip() for part in parts)
    return uuid.uuid5(uuid.NAMESPACE_URL, f"deca-growth:{namespace}:{value}").hex


def slug_part(value):
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", str(value or "")).strip()
    if not cleaned:
        return "Item"
    return "".join(part[:1].upper() + part[1:] for part in cleaned.split())


def code_from_name(value):
    cleaned = re.sub(r"[^a-zA-Z0-9 ]+", " ", str(value or "")).strip()
    if not cleaned:
        return "APP"

    alias = re.sub(r"\s+", "", cleaned).lower()
    if alias in {"delust", "dl"}:
        return "DL"

    compact = re.sub(r"\s+", "", cleaned)
    if len(compact) <= 4:
        return compact.upper()

    initials = "".join(part[:1] for part in cleaned.split())
    return (initials or compact[:4]).upper()


def build_automation_prefix(product, country, concept):
    country_code = (
        country.get("reelFarmCode")
        or COUNTRY_CODES.get(country.get("name"))
        or code_from_name(country.get("name"))
    ).upper()
    product_code = (product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
    topic = slug_part(concept.get("group") or "Topic")
    format_name = slug_part(concept.get("name") or "Format")
    return f"{country_code}-{product_code}-{topic}-{format_name}"


def build_country_automation_prefix(product, country):
    country_code = (
        country.get("reelFarmCode")
        or COUNTRY_CODES.get(country.get("name"))
        or code_from_name(country.get("name"))
    ).upper()
    product_code = (product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
    return f"{country_code}-{product_code}"


def automation_prefix_candidates(prefix):
    clean = str(prefix or "").strip()
    if not clean:
        return []

    candidates = [clean]
    parts = [part for part in re.split(r"[-_]+", clean) if part]
    if len(parts) >= 2:
        reversed_first_pair = "-".join([parts[1], parts[0], *parts[2:]])
        candidates.append(reversed_first_pair)

    deduped = []
    seen = set()
    for candidate in candidates:
        key = candidate.upper()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def automation_title_matches_prefix(title, prefix):
    clean_title = str(title or "").strip().upper()
    clean_prefix = str(prefix or "").strip().upper()
    if not clean_title or not clean_prefix:
        return False
    return (
        clean_title == clean_prefix
        or clean_title.startswith(f"{clean_prefix}-")
        or clean_title.startswith(f"{clean_prefix}_")
    )


def prefixes_equivalent(left, right):
    left_values = {candidate.upper() for candidate in automation_prefix_candidates(left)}
    right_value = str(right or "").strip().upper()
    return bool(right_value and right_value in left_values)


def normalize_username(value):
    return re.sub(r"[^a-z0-9_.]+", "", str(value or "").strip().lower().lstrip("@"))


def default_data():
    return [
        {
            "id": generate_id(),
            "name": "Product A",
            "logo": "",
            "countries": [
                {
                    "id": generate_id(),
                    "name": "United States",
                    "concepts": [
                        {"id": generate_id(), "name": "Tech Focus", "count": 45},
                        {"id": generate_id(), "name": "Lifestyle", "count": 30},
                    ],
                },
                {
                    "id": generate_id(),
                    "name": "Japan",
                    "concepts": [
                        {"id": generate_id(), "name": "Design/Aesthetics", "count": 50},
                    ],
                },
            ],
        },
        {
            "id": generate_id(),
            "name": "Product B",
            "logo": "",
            "countries": [
                {
                    "id": generate_id(),
                    "name": "Germany",
                    "concepts": [
                        {"id": generate_id(), "name": "Efficiency", "count": 28},
                        {"id": generate_id(), "name": "Sustainability", "count": 18},
                    ],
                }
            ],
        },
    ]


def initial_data():
    if SEED_DATA_PATH.is_file():
        try:
            payload = json.loads(SEED_DATA_PATH.read_text(encoding="utf-8"))
            data = payload.get("data")
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError):
            pass

    return default_data()


def connect_db():
    if using_postgres():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError(
                "DATABASE_URL is set, but psycopg is not installed. "
                "Run: pip install -r requirements.txt"
            ) from error

        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn, table, column):
    if using_postgres():
        placeholder = db_placeholder()
        row = conn.execute(
            f"""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = {placeholder}
              AND column_name = {placeholder}
            LIMIT 1
            """,
            (table, column),
        ).fetchone()
        return bool(row)

    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(row["name"]) == column for row in rows)


def ensure_column(conn, table, column, definition):
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_relational_schema(conn):
    statements = [
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            owner_type TEXT,
            logo_url TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS markets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_markets (
            id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            market_id TEXT NOT NULL,
            UNIQUE(product_id, market_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_market_channels (
            id TEXT PRIMARY KEY,
            product_market_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            UNIQUE(product_market_id, channel_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            product_market_channel_id TEXT NOT NULL,
            reelfarm_account_id TEXT,
            username TEXT,
            display_name TEXT,
            avatar_url TEXT,
            status TEXT,
            UNIQUE(product_market_channel_id, reelfarm_account_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS automations (
            id TEXT PRIMARY KEY,
            product_market_channel_id TEXT NOT NULL,
            account_id TEXT,
            reelfarm_automation_id TEXT NOT NULL UNIQUE,
            name TEXT,
            status TEXT,
            schedule TEXT,
            settings_json TEXT,
            post_mode TEXT,
            publish_method TEXT,
            created_at TEXT,
            synced_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            UNIQUE(product_id, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS formats (
            id TEXT PRIMARY KEY,
            concept_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            UNIQUE(concept_id, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS materials (
            id TEXT PRIMARY KEY,
            automation_id TEXT NOT NULL,
            product_market_channel_id TEXT NOT NULL,
            account_id TEXT,
            concept_id TEXT,
            format_id TEXT,
            reelfarm_video_id TEXT NOT NULL UNIQUE,
            video_type TEXT,
            hook TEXT,
            prompt TEXT,
            images_json TEXT,
            slide_count INTEGER,
            status TEXT,
            created_at TEXT,
            finished_at TEXT,
            synced_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            material_id TEXT NOT NULL,
            account_id TEXT,
            reelfarm_post_id TEXT NOT NULL UNIQUE,
            status TEXT,
            title TEXT,
            published_at TEXT,
            published_at_readable TEXT,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            share_count INTEGER,
            bookmark_count INTEGER,
            synced_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS post_daily_snapshots (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            share_count INTEGER,
            bookmark_count INTEGER,
            synced_at TEXT NOT NULL,
            UNIQUE(post_id, snapshot_date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS account_tags (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(account_id, tag)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS account_issues (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            issue TEXT NOT NULL,
            source TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(account_id, issue)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_tags (
            id TEXT PRIMARY KEY,
            product_code TEXT NOT NULL,
            tag TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(product_code, tag)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_daily_growth_snapshots (
            id TEXT PRIMARY KEY,
            product_code TEXT NOT NULL,
            report_date TEXT NOT NULL,
            report_timezone TEXT NOT NULL,
            source_timezone TEXT NOT NULL,
            utc_start TEXT NOT NULL,
            utc_end TEXT NOT NULL,
            source_date_from TEXT,
            source_date_to TEXT,
            reelfarm_views INTEGER,
            clone_views INTEGER,
            total_views INTEGER,
            download_count INTEGER,
            onboarding_unique INTEGER,
            synced_at TEXT NOT NULL,
            UNIQUE(product_code, report_date)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_post_daily_snapshots_snapshot_date ON post_daily_snapshots(snapshot_date)",
        "CREATE INDEX IF NOT EXISTS idx_post_daily_snapshots_post_id ON post_daily_snapshots(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_account_tags_account_id ON account_tags(account_id)",
        "CREATE INDEX IF NOT EXISTS idx_account_tags_tag ON account_tags(tag)",
        "CREATE INDEX IF NOT EXISTS idx_account_issues_account_id ON account_issues(account_id)",
        "CREATE INDEX IF NOT EXISTS idx_account_issues_issue ON account_issues(issue)",
        "CREATE INDEX IF NOT EXISTS idx_product_tags_product_code ON product_tags(product_code)",
        "CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at)",
        "CREATE INDEX IF NOT EXISTS idx_posts_material_id ON posts(material_id)",
        "CREATE INDEX IF NOT EXISTS idx_materials_automation_id ON materials(automation_id)",
        "CREATE INDEX IF NOT EXISTS idx_automations_product_market_channel_id ON automations(product_market_channel_id)",
        "CREATE INDEX IF NOT EXISTS idx_product_daily_growth_snapshots_product_date ON product_daily_growth_snapshots(product_code, report_date)",
        "CREATE INDEX IF NOT EXISTS idx_product_daily_growth_snapshots_report_date ON product_daily_growth_snapshots(report_date)",
    ]
    for statement in statements:
        conn.execute(statement)
    ensure_column(conn, "automations", "post_mode", "TEXT")
    ensure_column(conn, "automations", "publish_method", "TEXT")


def init_db():
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        init_relational_schema(conn)
        placeholder = db_placeholder()
        row = conn.execute(
            f"SELECT key FROM app_state WHERE key = {placeholder}",
            (STATE_KEY,),
        ).fetchone()
        if row is None:
            save_data(initial_data(), conn)
        conn.commit()


def save_app_value(key, value, conn=None):
    payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat()
    owns_connection = conn is None
    if owns_connection:
        conn = connect_db()
    try:
        placeholder = db_placeholder()
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


def load_app_value(key):
    init_db()
    with connect_db() as conn:
        placeholder = db_placeholder()
        row = conn.execute(
            f"SELECT value FROM app_state WHERE key = {placeholder}",
            (key,),
        ).fetchone()
    return row["value"] if row else ""


def delete_app_value(key):
    init_db()
    with connect_db() as conn:
        placeholder = db_placeholder()
        conn.execute(f"DELETE FROM app_state WHERE key = {placeholder}", (key,))
        conn.commit()


def save_data(data, conn=None):
    payload = json.dumps(strip_reelfarm_state(data), ensure_ascii=False, separators=(",", ":"))
    save_app_value(STATE_KEY, payload, conn)


def default_publish_check_state():
    return {"assignments": [], "last_result": None}


def load_publish_check_state():
    raw = load_app_value(PUBLISH_CHECK_STATE_KEY)
    if not raw:
        return default_publish_check_state()
    try:
        state = json.loads(raw)
    except json.JSONDecodeError:
        return default_publish_check_state()
    if not isinstance(state, dict):
        return default_publish_check_state()
    assignments = state.get("assignments")
    if not isinstance(assignments, list):
        assignments = []
    return {
        "assignments": assignments,
        "last_result": state.get("last_result") if isinstance(state.get("last_result"), dict) else None,
    }


def save_publish_check_state(state):
    clean = default_publish_check_state()
    assignments = state.get("assignments") if isinstance(state, dict) else []
    if isinstance(assignments, list):
        clean["assignments"] = [
            {
                "id": str(item.get("id") or generate_id()),
                "person_id": str(item.get("person_id") or ""),
                "person_name": str(item.get("person_name") or ""),
                "product_id": str(item.get("product_id") or ""),
                "country_id": str(item.get("country_id") or ""),
            }
            for item in assignments
            if isinstance(item, dict) and item.get("product_id") and item.get("country_id")
        ]
    if isinstance(state, dict) and isinstance(state.get("last_result"), dict):
        clean["last_result"] = state["last_result"]
    save_app_value(PUBLISH_CHECK_STATE_KEY, clean)
    return clean


def strip_reelfarm_state(value):
    if isinstance(value, list):
        return [strip_reelfarm_state(item) for item in value]
    if not isinstance(value, dict):
        return value

    clean = {}
    for key, item in value.items():
        if key == "reelFarmResult":
            continue
        clean[key] = strip_reelfarm_state(item)
    return clean


def db_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def int_or_none(value):
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def bool_from_api(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if text in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return False


def nested_value(payload, keys):
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload:
            return payload.get(key)
    for value in payload.values():
        if isinstance(value, dict):
            found = nested_value(value, keys)
            if found is not None:
                return found
    return None


REELFARM_POST_AS_DRAFT_KEYS = {
    "post_as_draft",
    "postAsDraft",
    "post_as_draft_enabled",
    "postAsDraftEnabled",
}


def reelfarm_tiktok_post_settings(automation):
    if not isinstance(automation, dict):
        return {}
    settings = automation.get("tiktok_post_settings")
    if isinstance(settings, dict):
        return settings
    settings = automation.get("tiktokPostSettings")
    if isinstance(settings, dict):
        return settings
    return {}


def reelfarm_post_mode(automation):
    settings = reelfarm_tiktok_post_settings(automation)
    post_mode = str(settings.get("post_mode") or settings.get("postMode") or "").strip().upper()
    if post_mode:
        return post_mode
    auto_post = settings.get("auto_post", settings.get("autoPost"))
    if auto_post is not None:
        return "DIRECT_POST" if bool_from_api(auto_post) else "MEDIA_UPLOAD"
    return ""


def reelfarm_post_as_draft_value(automation):
    post_mode = reelfarm_post_mode(automation)
    if post_mode:
        return post_mode == "MEDIA_UPLOAD"

    exact = nested_value(automation, REELFARM_POST_AS_DRAFT_KEYS)
    if exact is not None:
        return exact

    def walk(payload):
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized = re.sub(r"[^a-z0-9]+", "", str(key).lower())
                if "draft" in normalized and ("post" in normalized or "publish" in normalized):
                    return value
                found = walk(value)
                if found is not None:
                    return found
        elif isinstance(payload, list):
            for value in payload:
                found = walk(value)
                if found is not None:
                    return found
        return None

    return walk(automation)


def reelfarm_publish_method(automation):
    post_as_draft = reelfarm_post_as_draft_value(automation)
    return "manual" if bool_from_api(post_as_draft) else "api"


def data_source_channel_code(source):
    return "MUSEON_CLONE" if str(source or "").strip().lower() in {"museon_clone", "clone", "museon"} else "TIKTOK"


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    placeholder = db_placeholder()
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


def parse_concept_format_from_automation(title, country_code, product_code):
    clean_title = str(title or "").strip()
    prefixes = [
        f"{country_code}-{product_code}",
        f"{product_code}-{country_code}",
    ]
    matched_prefix = ""
    for prefix in prefixes:
        if automation_title_matches_prefix(clean_title, prefix):
            matched_prefix = prefix.upper()
            break
    if not matched_prefix:
        return "", ""

    remainder = clean_title[len(matched_prefix):].lstrip("-_")
    parts = [part for part in re.split(r"[-_]+", remainder) if part]
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    if len(parts) < 2:
        return "", ""

    return parts[0], "-".join(parts[1:])


def utc_snapshot_date(value=None):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def relational_table_counts(conn):
    counts = {}
    for table in (
        "products",
        "markets",
        "channels",
        "product_markets",
        "product_market_channels",
        "accounts",
        "automations",
        "concepts",
        "formats",
        "materials",
        "posts",
        "post_daily_snapshots",
        "product_daily_growth_snapshots",
    ):
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        counts[table] = int(row["count"] if row else 0)
    return counts


def project_products_to_relational(data=None, product_code_filter="", market_code_filter=""):
    data = data if isinstance(data, list) else load_data()
    now = datetime.now(timezone.utc).isoformat()
    channel_id = stable_id("channel", "TIKTOK")
    product_code_filter = str(product_code_filter or "").strip().upper()
    market_code_filter = str(market_code_filter or "").strip().upper()

    with connect_db() as conn:
        init_relational_schema(conn)
        zero_play_candidates = {}
        upsert_row(
            conn,
            "channels",
            {"id": channel_id, "name": "TikTok", "code": "TIKTOK"},
            ["code"],
        )

        for product in data:
            if not isinstance(product, dict):
                continue

            product_id = str(product.get("id") or stable_id("product", product.get("name")))
            product_code = (product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
            if product_code_filter and product_code != product_code_filter:
                continue

            upsert_row(
                conn,
                "products",
                {
                    "id": product_id,
                    "name": str(product.get("name") or "Untitled Product"),
                    "code": product_code,
                    "owner_type": product.get("folder") or product.get("owner_type"),
                    "logo_url": product.get("logo") or "",
                    "created_at": product.get("created_at") or now,
                    "updated_at": now,
                },
                ["id"],
            )

            for country in product.get("countries", []) or []:
                if not isinstance(country, dict):
                    continue

                market_code = (
                    country.get("reelFarmCode")
                    or COUNTRY_CODES.get(country.get("name"))
                    or code_from_name(country.get("name"))
                ).upper()
                if market_code_filter and market_code != market_code_filter:
                    continue

                market_id = stable_id("market", market_code)
                product_market_id = stable_id("product_market", product_id, market_id)
                product_market_channel_id = stable_id("product_market_channel", product_market_id, channel_id)

                upsert_row(
                    conn,
                    "markets",
                    {"id": market_id, "name": str(country.get("name") or market_code), "code": market_code},
                    ["code"],
                )
                upsert_row(
                    conn,
                    "product_markets",
                    {"id": product_market_id, "product_id": product_id, "market_id": market_id},
                    ["product_id", "market_id"],
                )
                upsert_row(
                    conn,
                    "product_market_channels",
                    {
                        "id": product_market_channel_id,
                        "product_market_id": product_market_id,
                        "channel_id": channel_id,
                    },
                    ["product_market_id", "channel_id"],
                )

                for concept in country.get("concepts", []) or []:
                    if not isinstance(concept, dict):
                        continue
                    concept_name = str(concept.get("group") or "默认 Topic").strip() or "默认 Topic"
                    format_name = str(concept.get("name") or "默认 Format").strip() or "默认 Format"
                    concept_id = stable_id("concept", product_id, concept_name)
                    format_id = stable_id("format", concept_id, format_name)
                    upsert_row(
                        conn,
                        "concepts",
                        {"id": concept_id, "product_id": product_id, "name": concept_name, "description": ""},
                        ["product_id", "name"],
                    )
                    upsert_row(
                        conn,
                        "formats",
                        {"id": format_id, "concept_id": concept_id, "name": format_name, "description": ""},
                        ["concept_id", "name"],
                    )

                result = country.get("reelFarmResult") if isinstance(country.get("reelFarmResult"), dict) else {}
                synced_at = country.get("reelFarmSyncedAt") or now
                for card in result.get("cards", []) or []:
                    if not isinstance(card, dict):
                        continue

                    account = card.get("account") if isinstance(card.get("account"), dict) else {}
                    automation = card.get("automation") if isinstance(card.get("automation"), dict) else {}
                    automation_reelfarm_id = str(
                        automation.get("automation_id") or stable_id("automation_source", automation.get("title"))
                    )
                    automation_title = str(automation.get("title") or automation_reelfarm_id)
                    reelfarm_account_id = str(
                        account.get("tiktok_account_id")
                        or automation.get("tiktok_account_id")
                        or account.get("account_username")
                        or automation_reelfarm_id
                    )
                    account_id = stable_id("account", product_market_channel_id, reelfarm_account_id)
                    automation_id = stable_id("automation", automation_reelfarm_id)
                    zero_play_candidates.setdefault(account_id, [])

                    upsert_row(
                        conn,
                        "accounts",
                        {
                            "id": account_id,
                            "product_market_channel_id": product_market_channel_id,
                            "reelfarm_account_id": reelfarm_account_id,
                            "username": account.get("account_username") or account.get("account_name") or "",
                            "display_name": account.get("account_name") or "",
                            "avatar_url": account.get("account_image") or "",
                            "status": account.get("status") or automation.get("status") or "",
                        },
                        ["product_market_channel_id", "reelfarm_account_id"],
                    )
                    upsert_row(
                        conn,
                        "automations",
                        {
                            "id": automation_id,
                            "product_market_channel_id": product_market_channel_id,
                            "account_id": account_id,
                            "reelfarm_automation_id": automation_reelfarm_id,
                            "name": automation_title,
                            "status": automation.get("status") or "",
                            "schedule": db_json(automation.get("schedule", [])),
                            "settings_json": db_json(automation),
                            "post_mode": automation.get("post_mode") or reelfarm_post_mode(automation),
                            "publish_method": automation.get("publish_method") or reelfarm_publish_method(automation),
                            "created_at": automation.get("created_at") or "",
                            "synced_at": synced_at,
                        },
                        ["reelfarm_automation_id"],
                    )

                    concept_name, format_name = parse_concept_format_from_automation(
                        automation_title,
                        market_code,
                        product_code,
                    )
                    concept_id = None
                    format_id = None
                    if concept_name and format_name:
                        concept_id = stable_id("concept", product_id, concept_name)
                        format_id = stable_id("format", concept_id, format_name)
                        upsert_row(
                            conn,
                            "concepts",
                            {"id": concept_id, "product_id": product_id, "name": concept_name, "description": ""},
                            ["product_id", "name"],
                        )
                        upsert_row(
                            conn,
                            "formats",
                            {"id": format_id, "concept_id": concept_id, "name": format_name, "description": ""},
                            ["concept_id", "name"],
                        )

                    posts_by_video = {
                        str(post.get("video_id")): post
                        for post in (card.get("posts") or [])
                        if isinstance(post, dict)
                    }
                    for video in card.get("videos", []) or []:
                        if not isinstance(video, dict):
                            continue
                        reelfarm_video_id = str(video.get("video_id") or video.get("id") or "")
                        if not reelfarm_video_id:
                            continue
                        material_id = stable_id("material", reelfarm_video_id)
                        images = video.get("slideshow_images") if isinstance(video.get("slideshow_images"), list) else []
                        upsert_row(
                            conn,
                            "materials",
                            {
                                "id": material_id,
                                "automation_id": automation_id,
                                "product_market_channel_id": product_market_channel_id,
                                "account_id": account_id,
                                "concept_id": concept_id,
                                "format_id": format_id,
                                "reelfarm_video_id": reelfarm_video_id,
                                "video_type": video.get("video_type") or "",
                                "hook": video.get("hook") or "",
                                "prompt": video.get("prompt") or "",
                                "images_json": db_json(images),
                                "slide_count": int_or_none(video.get("slide_count")) or len(images),
                                "status": video.get("status") or "",
                                "created_at": video.get("created_at") or "",
                                "finished_at": video.get("finished_at") or "",
                                "synced_at": synced_at,
                            },
                            ["reelfarm_video_id"],
                        )

                        post = posts_by_video.get(reelfarm_video_id)
                        if not isinstance(post, dict):
                            continue
                        reelfarm_post_id = str(post.get("post_id") or stable_id("post_source", material_id))
                        post_id = stable_id("post", reelfarm_post_id)
                        snapshot_date = utc_snapshot_date()
                        collect_zero_play_issue_candidate(
                            zero_play_candidates,
                            account_id,
                            post.get("published_at"),
                            post.get("view_count"),
                            business_date_string(synced_at),
                        )
                        upsert_row(
                            conn,
                            "posts",
                            {
                                "id": post_id,
                                "material_id": material_id,
                                "account_id": account_id,
                                "reelfarm_post_id": reelfarm_post_id,
                                "status": post.get("status") or "",
                                "title": post.get("title") or "",
                                "published_at": post.get("published_at") or "",
                                "published_at_readable": post.get("published_at_readable") or "",
                                "view_count": int_or_none(post.get("view_count")),
                                "like_count": int_or_none(post.get("like_count")),
                                "comment_count": int_or_none(post.get("comment_count")),
                                "share_count": int_or_none(post.get("share_count")),
                                "bookmark_count": int_or_none(post.get("bookmark_count")),
                                "synced_at": synced_at,
                            },
                            ["reelfarm_post_id"],
                        )
                        upsert_row(
                            conn,
                            "post_daily_snapshots",
                            {
                                "id": stable_id("post_daily_snapshot", post_id, snapshot_date),
                                "post_id": post_id,
                                "snapshot_date": snapshot_date,
                                "view_count": int_or_none(post.get("view_count")),
                                "like_count": int_or_none(post.get("like_count")),
                                "comment_count": int_or_none(post.get("comment_count")),
                                "share_count": int_or_none(post.get("share_count")),
                                "bookmark_count": int_or_none(post.get("bookmark_count")),
                                "synced_at": synced_at,
                            },
                            ["post_id", "snapshot_date"],
                        )

        apply_zero_play_issues(conn, zero_play_candidates, now)
        counts = relational_table_counts(conn)
        conn.commit()

    return {
        "ok": True,
        "projected_at": now,
        "database_backend": "postgres" if using_postgres() else "sqlite",
        "filters": {
            "product_code": product_code_filter or None,
            "market_code": market_code_filter or None,
        },
        "tables": counts,
    }


def project_synced_country_to_relational(product, country):
    if not isinstance(product, dict) or not isinstance(country, dict):
        return None

    scoped_product = dict(product)
    scoped_country = dict(country)
    scoped_product["countries"] = [scoped_country]
    product_code = (scoped_product.get("reelFarmCode") or code_from_name(scoped_product.get("name"))).upper()
    market_code = (
        scoped_country.get("reelFarmCode")
        or COUNTRY_CODES.get(scoped_country.get("name"))
        or code_from_name(scoped_country.get("name"))
    ).upper()
    return project_products_to_relational(
        data=[scoped_product],
        product_code_filter=product_code,
        market_code_filter=market_code,
    )


def parse_json_list(value):
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def stored_reelfarm_country(product_code, market_code):
    product_code = str(product_code or "").strip().upper()
    market_code = str(market_code or "").strip().upper()
    if not product_code or not market_code:
        raise ValueError("Missing product_code or country_code.")

    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                a.id AS automation_internal_id,
                a.reelfarm_automation_id,
                a.name AS automation_name,
                a.status AS automation_status,
                a.schedule AS automation_schedule,
                a.post_mode AS automation_post_mode,
                a.publish_method AS automation_publish_method,
                a.created_at AS automation_created_at,
                acc.reelfarm_account_id,
                acc.username AS account_username,
                acc.display_name AS account_name,
                acc.avatar_url AS account_image,
                mat.reelfarm_video_id,
                mat.created_at AS material_created_at,
                mat.finished_at AS material_finished_at,
                mat.status AS material_status,
                mat.video_type,
                mat.hook,
                mat.prompt,
                mat.images_json,
                mat.slide_count,
                post.reelfarm_post_id,
                post.status AS post_status,
                post.title AS post_title,
                post.published_at,
                post.published_at_readable,
                post.view_count,
                post.like_count,
                post.comment_count,
                post.share_count,
                post.bookmark_count
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            JOIN automations a ON a.product_market_channel_id = pmc.id
            LEFT JOIN accounts acc ON acc.id = a.account_id
            LEFT JOIN materials mat ON mat.automation_id = a.id
            LEFT JOIN posts post ON post.material_id = mat.id
            WHERE p.code = {placeholder}
              AND m.code = {placeholder}
              AND ch.code = {placeholder}
            ORDER BY a.name, mat.created_at DESC, post.published_at DESC
            """,
            (product_code, market_code, "TIKTOK"),
        ).fetchall()

    cards_by_id = {}
    for row in rows:
        automation_id = row["reelfarm_automation_id"]
        if not automation_id:
            continue

        if automation_id not in cards_by_id:
            account_id = row["reelfarm_account_id"] or ""
            cards_by_id[automation_id] = {
                "automation": {
                    "automation_id": automation_id,
                    "title": row["automation_name"],
                    "status": row["automation_status"],
                    "tiktok_account_id": account_id,
                    "schedule": parse_json_list(row["automation_schedule"]),
                    "post_mode": row["automation_post_mode"] or "",
                    "publish_method": row["automation_publish_method"] or "api",
                    "created_at": row["automation_created_at"],
                },
                "account": {
                    "tiktok_account_id": account_id,
                    "account_name": row["account_name"],
                    "account_username": row["account_username"],
                    "account_image": row["account_image"],
                },
                "videos": [],
                "video_total": 0,
                "posts": [],
                "post_statistics": {},
                "errors": {"videos": None, "posts": None},
            }

        card = cards_by_id[automation_id]
        video_id = row["reelfarm_video_id"]
        if video_id and not any(str(video.get("video_id")) == str(video_id) for video in card["videos"]):
            card["videos"].append(
                {
                    "video_id": video_id,
                    "created_at": row["material_created_at"],
                    "finished_at": row["material_finished_at"],
                    "status": row["material_status"],
                    "finished": row["material_status"] == "Finished",
                    "failed": False,
                    "video_type": row["video_type"],
                    "video_url": None,
                    "slideshow_images": parse_json_list(row["images_json"]),
                    "slide_count": int_or_none(row["slide_count"]) or 0,
                    "hook": row["hook"] or "",
                    "prompt": row["prompt"] or "",
                }
            )

        post_id = row["reelfarm_post_id"]
        if post_id and not any(str(post.get("post_id")) == str(post_id) for post in card["posts"]):
            card["posts"].append(
                {
                    "post_id": post_id,
                    "video_id": video_id,
                    "status": row["post_status"],
                    "title": row["post_title"],
                    "account_username": row["account_username"],
                    "published_at": row["published_at"],
                    "published_at_meta": row["published_at"],
                    "published_at_readable": row["published_at_readable"],
                    "view_count": row["view_count"],
                    "like_count": row["like_count"],
                    "comment_count": row["comment_count"],
                    "share_count": row["share_count"],
                    "bookmark_count": row["bookmark_count"],
                }
            )

    cards = list(cards_by_id.values())
    for card in cards:
        card["video_total"] = len(card["videos"])

    return {
        "prefix": f"{market_code}-{product_code}",
        "count": len(cards),
        "cards": cards,
    }


def load_data():
    init_db()
    value = load_app_value(STATE_KEY)

    if not value:
        data = default_data()
        save_data(data)
        return data

    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        data = default_data()
        save_data(data)
        return data

    if not isinstance(data, list):
        return default_data()

    clean_data = strip_reelfarm_state(data)
    if clean_data != data:
        save_data(clean_data)
    return clean_data


def enrich_data_with_relational_rollups(data):
    if not isinstance(data, list):
        return data

    enriched = json.loads(json.dumps(data, ensure_ascii=False))
    rollups = {}
    product_rollups = {}
    placeholder = db_placeholder()

    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                p.code AS product_code,
                m.code AS market_code,
                COUNT(DISTINCT acc.id) AS creator_count,
                COUNT(DISTINCT a.id) AS automation_count,
                COUNT(DISTINCT mat.id) AS material_count,
                COUNT(DISTINCT post.id) AS post_count,
                MAX(COALESCE(post.synced_at, mat.synced_at, a.synced_at)) AS last_synced_at
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            LEFT JOIN automations a ON a.product_market_channel_id = pmc.id
            LEFT JOIN accounts acc ON acc.id = a.account_id
            LEFT JOIN materials mat ON mat.automation_id = a.id
            LEFT JOIN posts post ON post.material_id = mat.id
            WHERE ch.code = {placeholder}
            GROUP BY p.code, m.code
            """,
            ("TIKTOK",),
        ).fetchall()

    for row in rows:
        product_code = str(row["product_code"] or "").upper()
        market_code = str(row["market_code"] or "").upper()
        item = {
            "creatorCount": int(row["creator_count"] or 0),
            "automationCount": int(row["automation_count"] or 0),
            "materialCount": int(row["material_count"] or 0),
            "postCount": int(row["post_count"] or 0),
            "reelFarmSyncedAt": row["last_synced_at"] or "",
        }
        rollups[(product_code, market_code)] = item
        product_rollup = product_rollups.setdefault(
            product_code,
            {"creatorCount": 0, "automationCount": 0, "materialCount": 0, "postCount": 0},
        )
        for key in ("creatorCount", "automationCount", "materialCount", "postCount"):
            product_rollup[key] += item[key]

    for product in enriched:
        if not isinstance(product, dict):
            continue
        product_code = (product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
        product.update(product_rollups.get(product_code, {
            "creatorCount": 0,
            "automationCount": 0,
            "materialCount": 0,
            "postCount": 0,
        }))
        product["countryCount"] = len(product.get("countries", []) or [])
        for country in product.get("countries", []) or []:
            if not isinstance(country, dict):
                continue
            market_code = (
                country.get("reelFarmCode")
                or COUNTRY_CODES.get(country.get("name"))
                or code_from_name(country.get("name"))
            ).upper()
            country.update(rollups.get((product_code, market_code), {
                "creatorCount": 0,
                "automationCount": 0,
                "materialCount": 0,
                "postCount": 0,
            }))

    return enriched


def hash_api_key(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def load_external_api_keys():
    value = load_app_value(EXTERNAL_API_KEYS_KEY)
    if not value:
        return []

    try:
        keys = json.loads(value)
    except json.JSONDecodeError:
        return []

    return keys if isinstance(keys, list) else []


def save_external_api_keys(keys):
    save_app_value(EXTERNAL_API_KEYS_KEY, keys if isinstance(keys, list) else [])


def public_external_api_key(key_record):
    return {
        "id": key_record.get("id"),
        "name": key_record.get("name"),
        "prefix": key_record.get("prefix"),
        "permissions": key_record.get("permissions", []),
        "active": bool(key_record.get("active")),
        "created_at": key_record.get("created_at"),
        "revoked_at": key_record.get("revoked_at"),
    }


def create_external_api_key(name, permissions=None):
    now = datetime.now(timezone.utc).isoformat()
    raw_key = f"deca_{secrets.token_urlsafe(32)}"
    key_record = {
        "id": generate_id(),
        "name": (name or "External AI").strip() or "External AI",
        "prefix": raw_key[:14],
        "key_hash": hash_api_key(raw_key),
        "permissions": permissions or ["materials:read"],
        "active": True,
        "created_at": now,
        "revoked_at": None,
    }
    keys = load_external_api_keys()
    keys.append(key_record)
    save_external_api_keys(keys)
    return {"key": raw_key, "record": public_external_api_key(key_record)}


def revoke_external_api_key(key_id):
    keys = load_external_api_keys()
    now = datetime.now(timezone.utc).isoformat()
    updated_record = None
    for key_record in keys:
        if str(key_record.get("id")) == str(key_id):
            key_record["active"] = False
            key_record["revoked_at"] = now
            updated_record = key_record
            break

    if updated_record is None:
        raise ValueError("API key not found.")

    save_external_api_keys(keys)
    return public_external_api_key(updated_record)


def list_external_api_keys():
    return [public_external_api_key(key_record) for key_record in load_external_api_keys()]


def external_api_key_authorized(token, permission):
    if not token:
        return False
    if AI_API_KEY and hmac.compare_digest(token, AI_API_KEY):
        return True

    token_hash = hash_api_key(token)
    for key_record in load_external_api_keys():
        if not key_record.get("active"):
            continue
        if permission not in (key_record.get("permissions") or []):
            continue
        if hmac.compare_digest(str(key_record.get("key_hash", "")), token_hash):
            return True

    return False


def reelfarm_api_key():
    return os.environ.get("REELFARM_API_KEY", "").strip() or load_app_value(REELFARM_API_KEY).strip()


def reelfarm_request(path, query=None):
    api_key = reelfarm_api_key()
    if not api_key:
        raise RuntimeError("ReelFarm API key is not configured.")

    url = f"{REELFARM_BASE_URL}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"

    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ManagementTable/1.0",
        },
    )

    try:
        with urlopen(request, timeout=25, context=make_ssl_context()) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ReelFarm API error {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach ReelFarm API: {error.reason}") from error


def list_payload(payload, key):
    value = payload.get(key) if isinstance(payload, dict) else None
    return value if isinstance(value, list) else []


def video_identifier(video):
    for key in ("video_id", "id", "uuid"):
        value = video.get(key)
        if value is not None:
            return str(value)
    return ""


def compact_automation(automation):
    return {
        "automation_id": automation.get("automation_id"),
        "title": automation.get("title"),
        "status": automation.get("status"),
        "tiktok_account_id": automation.get("tiktok_account_id"),
        "schedule": automation.get("schedule", []),
        "post_mode": reelfarm_post_mode(automation),
        "post_as_draft": reelfarm_post_as_draft_value(automation),
        "publish_method": reelfarm_publish_method(automation),
        "created_at": automation.get("created_at"),
    }


def compact_account(account):
    return {
        "tiktok_account_id": account.get("tiktok_account_id"),
        "account_name": account.get("account_name"),
        "account_username": account.get("account_username"),
        "account_image": account.get("account_image"),
    }


def compact_video(video):
    images = video.get("slideshow_images")
    if not isinstance(images, list):
        images = []

    prompt = video.get("prompt") or ""
    hook_match = re.search(
        r"(?:first slide text saying|first slide text says|first slide.*?saying)\s+['\"]([^'\"]+)['\"]",
        prompt,
        re.IGNORECASE,
    )

    return {
        "video_id": video.get("video_id") or video.get("id"),
        "created_at": video.get("created_at"),
        "finished_at": video.get("finished_at"),
        "status": video.get("status"),
        "finished": video.get("finished"),
        "failed": video.get("failed"),
        "video_type": video.get("video_type"),
        "video_url": video.get("video_url"),
        "slideshow_images": images,
        "slide_count": len(images),
        "hook": hook_match.group(1) if hook_match else "",
        "prompt": prompt,
    }


def readable_utc_datetime(value):
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""

    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return raw_value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y/%m/%d %H:%M UTC")


def parse_iso_datetime(value):
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def utc_date_string(value=None):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date().isoformat()
    parsed = parse_iso_datetime(value)
    if parsed:
        return parsed.astimezone(timezone.utc).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def business_date_string(value=None):
    if isinstance(value, datetime):
        return value.astimezone(BUSINESS_TIMEZONE).date().isoformat()
    parsed = parse_iso_datetime(value)
    if parsed:
        return parsed.astimezone(BUSINESS_TIMEZONE).date().isoformat()
    return datetime.now(BUSINESS_TIMEZONE).date().isoformat()


def collect_zero_play_issue_candidate(candidates, account_id, published_at, view_count, sync_date):
    account_id = str(account_id or "").strip()
    published = parse_iso_datetime(published_at)
    if not account_id or not published:
        return
    if published.astimezone(BUSINESS_TIMEZONE).date().isoformat() >= sync_date:
        return
    candidates.setdefault(account_id, []).append({
        "published_at": published,
        "view_count": int_or_none(view_count),
    })


def apply_zero_play_issues(conn, candidates, synced_at):
    placeholder = db_placeholder()
    now = synced_at or datetime.now(timezone.utc).isoformat()
    for account_id, posts in (candidates or {}).items():
        latest_posts = sorted(
            posts,
            key=lambda item: item.get("published_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[:ZERO_PLAY_POST_LIMIT]
        should_warn = len(latest_posts) == ZERO_PLAY_POST_LIMIT and all(
            item.get("view_count") == ZERO_PLAY_VIEW_THRESHOLD
            for item in latest_posts
        )
        if should_warn:
            upsert_row(
                conn,
                "account_issues",
                {
                    "id": stable_id("account_issue", account_id, ZERO_PLAY_ISSUE.lower()),
                    "account_id": account_id,
                    "issue": ZERO_PLAY_ISSUE,
                    "source": "auto",
                    "created_at": now,
                    "updated_at": now,
                },
                ["account_id", "issue"],
            )
        else:
            conn.execute(
                f"DELETE FROM account_issues WHERE account_id = {placeholder} AND issue = {placeholder} AND COALESCE(source, '') = {placeholder}",
                (account_id, ZERO_PLAY_ISSUE, "auto"),
            )


def compact_post(post):
    published_at = post.get("published_at")
    return {
        "post_id": post.get("post_id"),
        "video_id": post.get("video_id"),
        "status": post.get("status") or post.get("post_status"),
        "title": post.get("title"),
        "account_username": post.get("account_username"),
        "published_at": published_at,
        "published_at_meta": published_at,
        "published_at_readable": readable_utc_datetime(published_at),
        "view_count": post.get("view_count"),
        "like_count": post.get("like_count"),
        "comment_count": post.get("comment_count"),
        "share_count": post.get("share_count"),
        "bookmark_count": post.get("bookmark_count"),
    }


def reelfarm_matches(prefix):
    clean_prefix = (prefix or "").strip()
    if not clean_prefix:
        raise ValueError("Missing automation prefix.")

    candidates = automation_prefix_candidates(clean_prefix)
    automations_payload = reelfarm_request("/automations")
    automations = list_payload(automations_payload, "automations")
    matched = []
    seen_automation_keys = set()
    for automation in automations:
        title = str(automation.get("title", "") or "")
        if not any(automation_title_matches_prefix(title, candidate) for candidate in candidates):
            continue
        key = str(automation.get("automation_id") or title).strip()
        if key in seen_automation_keys:
            continue
        seen_automation_keys.add(key)
        matched.append(automation)

    accounts_by_id = {}
    try:
        accounts_payload = reelfarm_request("/tiktok/accounts")
        for account in list_payload(accounts_payload, "accounts"):
            account_id = account.get("tiktok_account_id")
            if account_id:
                accounts_by_id[account_id] = account
    except RuntimeError:
        accounts_by_id = {}

    def build_card(automation):
        automation_id = automation.get("automation_id")
        details = automation
        needs_details = (
            not automation.get("tiktok_account_id")
            or reelfarm_post_as_draft_value(automation) is None
        )
        if automation_id and needs_details:
            try:
                details = reelfarm_request(f"/automations/{quote(str(automation_id), safe='')}")
            except RuntimeError:
                details = automation

        tiktok_account_id = details.get("tiktok_account_id") or automation.get("tiktok_account_id")
        account = accounts_by_id.get(tiktok_account_id, {}) if tiktok_account_id else {}

        def fetch_videos():
            if not automation_id:
                return {"videos": [], "total": 0}
            try:
                return reelfarm_request(
                    "/videos",
                    {"automation_id": automation_id, "video_type": "slideshow", "limit": 50},
                )
            except RuntimeError as error:
                return {"videos": [], "total": 0, "error": str(error)}

        def fetch_posts():
            if not tiktok_account_id:
                return {"posts": [], "statistics": {}}
            try:
                return reelfarm_request(
                    "/tiktok/posts",
                    {
                        "tiktok_account_id": tiktok_account_id,
                        "timeframe": "all",
                        "sort": "recent",
                        "limit": 50,
                    },
                )
            except RuntimeError as error:
                return {"posts": [], "statistics": {}, "error": str(error)}

        with ThreadPoolExecutor(max_workers=2) as inner_executor:
            videos_future = inner_executor.submit(fetch_videos)
            posts_future = inner_executor.submit(fetch_posts)
            videos_payload = videos_future.result()
            posts_payload = posts_future.result()

        posts = [compact_post(post) for post in list_payload(posts_payload, "posts")]
        posted_video_ids = {
            str(post.get("video_id"))
            for post in posts
            if post.get("video_id") and (post.get("post_id") or post.get("published_at"))
        }
        posted_videos = [
            video
            for video in list_payload(videos_payload, "videos")
            if str(video.get("video_id") or video.get("id")) in posted_video_ids
        ]
        videos = [compact_video(video) for video in posted_videos[:50]]
        automation_posted_video_ids = {str(video.get("video_id")) for video in videos if video.get("video_id")}
        posts = [
            post
            for post in posts
            if str(post.get("video_id")) in automation_posted_video_ids
        ]

        return {
            "automation": compact_automation(details),
            "account": compact_account(account),
            "videos": videos,
            "video_total": len(videos),
            "posts": posts,
            "post_statistics": posts_payload.get("statistics", {})
            if isinstance(posts_payload, dict)
            else {},
            "errors": {
                "videos": videos_payload.get("error")
                if isinstance(videos_payload, dict)
                else None,
                "posts": posts_payload.get("error")
                if isinstance(posts_payload, dict)
                else None,
            },
        }

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(matched)))) as executor:
        cards = list(executor.map(build_card, matched))

    return {"prefix": clean_prefix, "matched_prefixes": candidates, "count": len(cards), "cards": cards}


def reelfarm_creator_count(result):
    cards = result.get("cards", []) if isinstance(result, dict) else []
    creator_keys = set()
    for card in cards:
        if not isinstance(card, dict):
            continue

        account = card.get("account") if isinstance(card.get("account"), dict) else {}
        automation = card.get("automation") if isinstance(card.get("automation"), dict) else {}
        creator_key = str(
            account.get("tiktok_account_id")
            or automation.get("tiktok_account_id")
            or account.get("account_username")
            or account.get("username")
            or account.get("account_name")
            or automation.get("automation_id")
            or automation.get("title")
            or ""
        ).strip()
        if creator_key:
            creator_keys.add(creator_key)

    return len(creator_keys)


def reelfarm_material_count(result):
    cards = result.get("cards", []) if isinstance(result, dict) else []
    return sum(
        len(card.get("videos", []) or [])
        for card in cards
        if isinstance(card, dict)
    )


def sync_all_reelfarm_records():
    if not reelfarm_api_key():
        raise RuntimeError("ReelFarm API key is not configured.")

    data = load_data()
    synced_at = datetime.now(timezone.utc).isoformat()
    successes = 0
    errors = []
    relational_projection = None

    for product in data:
        for country in product.get("countries", []) or []:
            prefix = build_country_automation_prefix(product, country)
            try:
                result = reelfarm_matches(prefix)
                country["reelFarmSyncedAt"] = synced_at
                country["creatorCount"] = reelfarm_creator_count(result)
                country["materialCount"] = reelfarm_material_count(result)
                scoped_country = dict(country)
                scoped_country["reelFarmResult"] = result
                relational_projection = project_synced_country_to_relational(
                    product,
                    scoped_country,
                )
                successes += 1
            except RuntimeError as error:
                errors.append({"prefix": prefix, "error": str(error)})

    save_data(data)
    return {
        "ok": True,
        "synced_at": synced_at,
        "synced_count": successes,
        "error_count": len(errors),
        "errors": errors[:20],
        "relational_projection": relational_projection,
    }


def sync_reelfarm_country(prefix, product_id="", country_id="", product_code="", country_code=""):
    clean_prefix = (prefix or "").strip()
    if not clean_prefix:
        raise ValueError("Missing automation prefix.")

    data = load_data()
    synced_at = datetime.now(timezone.utc).isoformat()

    for product in data:
        for country in product.get("countries", []) or []:
            id_match = (
                country_id
                and product_id
                and str(country.get("id")) == str(country_id)
                and str(product.get("id")) == str(product_id)
            )
            prefix_match = prefixes_equivalent(build_country_automation_prefix(product, country), clean_prefix)
            if not id_match and not prefix_match:
                continue

            if product_code:
                product["reelFarmCode"] = str(product_code).strip().upper()
            if country_code:
                country["reelFarmCode"] = str(country_code).strip().upper()

            result = reelfarm_matches(clean_prefix)
            country["reelFarmSyncedAt"] = synced_at
            country["creatorCount"] = reelfarm_creator_count(result)
            country["materialCount"] = reelfarm_material_count(result)
            scoped_country = dict(country)
            scoped_country["reelFarmResult"] = result
            relational_projection = project_synced_country_to_relational(product, scoped_country)
            save_data(data)
            return {
                "ok": True,
                "prefix": clean_prefix,
                "synced_at": synced_at,
                "creator_count": country["creatorCount"],
                "material_count": country["materialCount"],
                "relational_projection": relational_projection,
            }

    raise ValueError("No matching country found for this prefix.")


def sync_reelfarm_prefix(prefix, product_id="", country_id="", concept_id="", product_code="", country_code=""):
    clean_prefix = (prefix or "").strip()
    if not clean_prefix:
        raise ValueError("Missing automation prefix.")

    data = load_data()
    synced_at = datetime.now(timezone.utc).isoformat()

    for product in data:
        for country in product.get("countries", []) or []:
            for concept in country.get("concepts", []) or []:
                id_match = (
                    concept_id
                    and country_id
                    and product_id
                    and str(concept.get("id")) == str(concept_id)
                    and str(country.get("id")) == str(country_id)
                    and str(product.get("id")) == str(product_id)
                )
                prefix_match = prefixes_equivalent(build_automation_prefix(product, country, concept), clean_prefix)
                if not id_match and not prefix_match:
                    continue

                if product_code:
                    product["reelFarmCode"] = str(product_code).strip().upper()
                if country_code:
                    country["reelFarmCode"] = str(country_code).strip().upper()
                result = reelfarm_matches(clean_prefix)
                concept["reelFarmSyncedAt"] = synced_at
                concept["count"] = reelfarm_creator_count(result)
                save_data(data)
                return {
                    "ok": True,
                    "prefix": clean_prefix,
                    "synced_at": synced_at,
                    "creator_count": concept["count"],
                }

    raise ValueError("No matching Format found for this prefix.")


def cron_authorized(headers):
    secret = os.environ.get("CRON_SECRET", "").strip()
    if not secret:
        return True
    return headers.get("Authorization", "") == f"Bearer {secret}"


def password_hash(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def auth_signature(username, expires_at):
    payload = f"{username}|{expires_at}"
    return hmac.new(SESSION_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def make_auth_token(username):
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    signature = auth_signature(username, expires_at)
    return f"{username}|{expires_at}|{signature}"


def valid_auth_token(token):
    try:
        username, expires_at_text, signature = str(token or "").split("|", 2)
        expires_at = int(expires_at_text)
    except (TypeError, ValueError):
        return False

    if username != ADMIN_USERNAME or expires_at < int(time.time()):
        return False

    expected = auth_signature(username, expires_at)
    return hmac.compare_digest(signature, expected)


def cookie_header(name, value, max_age=None):
    parts = [
        f"{name}={value}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if max_age is not None:
        parts.append(f"Max-Age={int(max_age)}")
    return "; ".join(parts)


def database_snapshot():
    init_db()
    with connect_db() as conn:
        placeholder = db_placeholder()
        row = conn.execute(
            f"SELECT key, value, updated_at FROM app_state WHERE key = {placeholder}",
            (STATE_KEY,),
        ).fetchone()
        relational_counts = relational_table_counts(conn)

    data = load_data()
    countries_count = sum(len(product.get("countries", [])) for product in data)
    concepts_count = sum(
        len(country.get("concepts", []))
        for product in data
        for country in product.get("countries", [])
    )
    total_count = sum(
        int(concept.get("count", 0) or 0)
        for product in data
        for country in product.get("countries", [])
        for concept in country.get("concepts", [])
    )

    return {
        "database_path": str(DB_PATH),
        "database_backend": "postgres" if using_postgres() else "sqlite",
        "table": "app_state",
        "key": STATE_KEY,
        "updated_at": row["updated_at"] if row else None,
        "stats": {
            "products": len(data),
            "countries": countries_count,
            "concepts": concepts_count,
            "total_count": total_count,
        },
        "relational_tables": relational_counts,
        "data": data,
    }


DATA_QUERY_RESOURCES = {
    "summary",
    "product_kpis",
    "product_rollups",
    "country_cards",
    "countries",
    "accounts",
    "account_posts",
    "posts",
    "materials",
    "daily_metrics",
    "top_posts",
}
DATA_QUERY_METRICS = {"view_count", "like_count", "comment_count", "share_count", "bookmark_count"}


def query_value(query, key, default=""):
    value = query.get(key, [default])
    if isinstance(value, list):
        return str(value[0] if value else default).strip()
    return str(value or default).strip()


def query_limit_offset(query, default=50, max_limit=500):
    try:
        limit = int(query_value(query, "limit", default))
    except ValueError:
        limit = default
    try:
        offset = int(query_value(query, "offset", 0))
    except ValueError:
        offset = 0
    limit = max(1, min(max_limit, limit))
    offset = max(0, offset)
    return limit, offset


def query_days_window(query):
    try:
        days = int(query_value(query, "days", 0))
    except ValueError:
        days = 0
    if days <= 0:
        return "", ""
    days = min(days, 366)
    beijing = timezone(timedelta(hours=8))
    current = datetime.now(timezone.utc).astimezone(beijing)
    today_start_local = datetime(current.year, current.month, current.day, tzinfo=beijing)
    start_local = today_start_local - timedelta(days=days)
    end_local = today_start_local
    return start_local.astimezone(timezone.utc).isoformat(), end_local.astimezone(timezone.utc).isoformat()


def query_days_snapshot_window(query):
    try:
        days = int(query_value(query, "days", 0))
    except ValueError:
        days = 0
    if days <= 0:
        return "", ""
    days = min(days, 366)
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def post_datetime_bound(value, end=False):
    clean = str(value or "").strip()
    if not clean:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean):
        return f"{clean}T23:59:59.999999+00:00" if end else f"{clean}T00:00:00+00:00"
    return clean


def query_filters(query):
    product_code = query_value(query, "product_code").upper()
    market_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    return {
        "product_code": product_code or None,
        "country_code": market_code or None,
        "market_code": market_code or None,
        "account_id": query_value(query, "account_id") or None,
        "automation_id": query_value(query, "automation_id") or None,
        "material_id": query_value(query, "material_id") or None,
        "post_id": query_value(query, "post_id") or None,
        "date_from": query_value(query, "date_from") or None,
        "date_to": query_value(query, "date_to") or None,
        "days": query_value(query, "days") or None,
        "metric": query_value(query, "metric") or None,
        "include": query_value(query, "include") or None,
    }


def compact_filters(filters):
    return {key: value for key, value in filters.items() if value not in ("", None)}


def pagination_payload(limit, offset, rows, total=None):
    total_value = int(total if total is not None else max(offset + min(len(rows), limit), offset + limit + (1 if len(rows) > limit else 0)))
    return {
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total_value,
        "total": total_value,
    }


def row_dict(row):
    return dict(row) if row else {}


def common_where(query, date_column="post.published_at", include_post_dates=True):
    placeholder = db_placeholder()
    where = ["ch.code = " + placeholder]
    params = [data_source_channel_code(query_value(query, "source"))]
    product_code = query_value(query, "product_code").upper()
    market_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    account_id = query_value(query, "account_id")
    automation_id = query_value(query, "automation_id")
    material_id = query_value(query, "material_id")
    post_id = query_value(query, "post_id")
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if include_post_dates and not date_from and not date_to:
        date_from, date_to = query_days_window(query)

    if product_code:
        where.append("p.code = " + placeholder)
        params.append(product_code)
    if market_code:
        where.append("m.code = " + placeholder)
        params.append(market_code)
    if account_id:
        where.append(f"(acc.id = {placeholder} OR acc.reelfarm_account_id = {placeholder} OR acc.username = {placeholder})")
        params.extend([account_id, account_id, account_id.lstrip("@")])
    if automation_id:
        where.append(f"(a.id = {placeholder} OR a.reelfarm_automation_id = {placeholder})")
        params.extend([automation_id, automation_id])
    if material_id:
        where.append(f"(mat.id = {placeholder} OR mat.reelfarm_video_id = {placeholder})")
        params.extend([material_id, material_id])
    if post_id:
        where.append(f"(post.id = {placeholder} OR post.reelfarm_post_id = {placeholder})")
        params.extend([post_id, post_id])
    if include_post_dates and date_from:
        where.append(f"{date_column} >= {placeholder}")
        params.append(post_datetime_bound(date_from))
    if include_post_dates and date_to:
        where.append(f"{date_column} <= {placeholder}")
        params.append(post_datetime_bound(date_to, end=True))

    return " AND ".join(where), params


def relational_base_from():
    return """
        FROM products p
        JOIN product_markets pm ON pm.product_id = p.id
        JOIN markets m ON m.id = pm.market_id
        JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
        JOIN channels ch ON ch.id = pmc.channel_id
        LEFT JOIN automations a ON a.product_market_channel_id = pmc.id
        LEFT JOIN accounts acc ON acc.id = a.account_id
        LEFT JOIN materials mat ON mat.automation_id = a.id
        LEFT JOIN posts post ON post.material_id = mat.id
    """


def query_summary(query):
    where_sql, params = common_where(query)
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"""
            SELECT
                COUNT(DISTINCT p.id) AS products,
                COUNT(DISTINCT m.id) AS countries,
                COUNT(DISTINCT acc.id) AS accounts,
                COUNT(DISTINCT a.id) AS automations,
                COUNT(DISTINCT mat.id) AS materials,
                COUNT(DISTINCT post.id) AS posts,
                COALESCE(SUM(post.view_count), 0) AS total_views,
                COALESCE(SUM(post.like_count), 0) AS total_likes,
                COALESCE(SUM(post.comment_count), 0) AS total_comments,
                COALESCE(SUM(post.share_count), 0) AS total_shares,
                COALESCE(SUM(post.bookmark_count), 0) AS total_bookmarks,
                MAX(COALESCE(post.synced_at, mat.synced_at, a.synced_at)) AS last_synced_at
            {relational_base_from()}
            WHERE {where_sql}
            """,
            tuple(params),
        ).fetchone()
    return row_dict(row)


def query_country_cards(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    return stored_reelfarm_country(product_code, country_code)


def query_countries(query):
    where_sql, params = common_where(query, include_post_dates=False)
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                p.id AS product_id,
                p.code AS product_code,
                p.name AS product_name,
                m.id AS market_id,
                m.id AS country_id,
                m.code AS market_code,
                m.code AS country_code,
                m.name AS country_name,
                COUNT(DISTINCT acc.id) AS creator_count,
                COUNT(DISTINCT a.id) AS automation_count,
                COUNT(DISTINCT mat.id) AS material_count,
                COUNT(DISTINCT post.id) AS post_count,
                COALESCE(SUM(post.view_count), 0) AS total_views,
                COALESCE(SUM(post.like_count), 0) AS total_likes,
                COALESCE(SUM(post.comment_count), 0) AS total_comments,
                COALESCE(SUM(post.share_count), 0) AS total_shares,
                COALESCE(SUM(post.bookmark_count), 0) AS total_bookmarks,
                MAX(COALESCE(post.synced_at, mat.synced_at, a.synced_at)) AS last_synced_at
            {relational_base_from()}
            WHERE {where_sql}
            GROUP BY p.id, p.code, p.name, m.id, m.code, m.name
            ORDER BY p.name, m.code
            """,
            tuple(params),
        ).fetchall()
    return attach_account_issues([row_dict(row) for row in rows])


def query_product_kpis(query):
    channel_code = data_source_channel_code(query_value(query, "source"))
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    if not product_code:
        raise ValueError("product_code is required.")
    placeholder = db_placeholder()
    now_utc = datetime.now(timezone.utc)
    beijing = timezone(timedelta(hours=8))
    current_local = now_utc.astimezone(beijing)
    today_start_local = datetime(current_local.year, current_local.month, current_local.day, tzinfo=beijing)
    yesterday_start_local = today_start_local - timedelta(days=1)
    seven_start_local = yesterday_start_local - timedelta(days=6)
    seven_end_local = today_start_local
    yesterday_start = yesterday_start_local.astimezone(timezone.utc).isoformat()
    yesterday_end = today_start_local.astimezone(timezone.utc).isoformat()
    seven_start = seven_start_local.astimezone(timezone.utc).isoformat()
    seven_end = seven_end_local.astimezone(timezone.utc).isoformat()
    market_filter = ""
    filter_params = [channel_code, product_code]
    if country_code:
        market_filter = f" AND m.code = {placeholder}"
        filter_params.append(country_code)
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"""
            SELECT
                COUNT(DISTINCT CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN acc.id END) AS today_creators,
                COUNT(DISTINCT CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.id END) AS today_posts,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.view_count ELSE 0 END), 0) AS today_views,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.like_count ELSE 0 END), 0) AS today_likes,
                COUNT(DISTINCT CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN acc.id END) AS seven_day_creators,
                COUNT(DISTINCT CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.id END) AS seven_day_posts,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.view_count ELSE 0 END), 0) AS seven_day_views,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.like_count ELSE 0 END), 0) AS seven_day_likes,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.comment_count ELSE 0 END), 0) AS seven_day_comments,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.share_count ELSE 0 END), 0) AS seven_day_shares,
                COALESCE(SUM(CASE WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder} THEN post.bookmark_count ELSE 0 END), 0) AS seven_day_bookmarks
            {relational_base_from()}
            WHERE ch.code = {placeholder} AND p.code = {placeholder}{market_filter} AND post.id IS NOT NULL
            """,
            (
                yesterday_start, yesterday_end,
                yesterday_start, yesterday_end,
                yesterday_start, yesterday_end,
                yesterday_start, yesterday_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                seven_start, seven_end,
                *filter_params,
            ),
        ).fetchone()
        daily_rows = conn.execute(
            f"""
            SELECT acc.id AS account_id, post.published_at AS published_at
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}{market_filter}
              AND post.published_at >= {placeholder}
              AND post.published_at < {placeholder}
              AND post.id IS NOT NULL
            """,
            (*filter_params, seven_start, seven_end),
        ).fetchall()
    data = row_dict(row)
    daily_creator_sets = {
        (seven_start_local + timedelta(days=day_index)).date().isoformat(): set()
        for day_index in range(7)
    }
    for daily_row in daily_rows:
        daily_data = row_dict(daily_row)
        parsed = parse_iso_datetime(daily_data.get("published_at"))
        if not parsed:
            continue
        local_day = parsed.astimezone(beijing).date().isoformat()
        if local_day in daily_creator_sets and daily_data.get("account_id"):
            daily_creator_sets[local_day].add(daily_data["account_id"])
    average_daily_creators = sum(len(accounts) for accounts in daily_creator_sets.values()) / 7
    today_creators = int(data.get("today_creators") or 0)
    today_posts = int(data.get("today_posts") or 0)
    today_views = int(data.get("today_views") or 0)
    today_likes = int(data.get("today_likes") or 0)
    seven_creators = int(data.get("seven_day_creators") or 0)
    seven_posts = int(data.get("seven_day_posts") or 0)
    seven_views = int(data.get("seven_day_views") or 0)
    seven_likes = int(data.get("seven_day_likes") or 0)
    interactions = (
        seven_likes
        + int(data.get("seven_day_comments") or 0)
        + int(data.get("seven_day_shares") or 0)
        + int(data.get("seven_day_bookmarks") or 0)
    )
    return {
        "product_code": product_code,
        "country_code": country_code or None,
        "today": {
            "creators": today_creators,
            "posts": today_posts,
            "views": today_views,
            "likes": today_likes,
            "average_views": round(today_views / today_posts) if today_posts else 0,
            "utc_window": {"start": yesterday_start, "end": yesterday_end},
        },
        "seven_day": {
            "creators": seven_creators,
            "posts": seven_posts,
            "views": seven_views,
            "likes": seven_likes,
            "average_creators": average_daily_creators,
            "average_posts": seven_posts / 7,
            "average_views": round(seven_views / seven_posts) if seven_posts else 0,
            "average_views_per_day": seven_views / 7,
            "average_likes": seven_likes / 7,
            "average_er": (interactions / seven_views * 100) if seven_views else 0,
            "interactions": interactions,
            "utc_window": {"start": seven_start, "end": seven_end},
        },
    }


def museon_post_published_at(post):
    return post.get("published_at") or post.get("created_at") or post.get("posted_at") or ""


def query_museon_clone_product_kpis(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    if not product_code:
        raise ValueError("product_code is required.")

    beijing = timezone(timedelta(hours=8))
    current_local = datetime.now(timezone.utc).astimezone(beijing)
    today_start_local = datetime(current_local.year, current_local.month, current_local.day, tzinfo=beijing)
    yesterday_start_local = today_start_local - timedelta(days=1)
    seven_start_local = yesterday_start_local - timedelta(days=6)
    seven_end_local = today_start_local
    yesterday_start_dt = yesterday_start_local.astimezone(timezone.utc)
    yesterday_end_dt = today_start_local.astimezone(timezone.utc)
    seven_start_dt = seven_start_local.astimezone(timezone.utc)
    seven_end_dt = seven_end_local.astimezone(timezone.utc)

    today_creators = set()
    seven_creators = set()
    daily_creator_sets = {
        (seven_start_local + timedelta(days=day_index)).date().isoformat(): set()
        for day_index in range(7)
    }
    today_posts = today_views = today_likes = 0
    seven_posts = seven_views = seven_likes = 0
    seven_comments = seven_shares = seven_bookmarks = 0

    for context in museon_clone_campaigns_for_product(product_code, country_code):
        campaign = context.get("campaign")
        if not campaign:
            continue
        posts = museon_all_posts(campaign.get("id"), seven_start_dt.isoformat(), seven_end_dt.isoformat())
        for post in posts:
            published = parse_iso_datetime(museon_post_published_at(post))
            if not published:
                continue
            account = museon_account_from_post(post)
            account_key = normalize_username(account.get("username")) or str(account.get("id") or "")
            metrics = museon_post_metrics(post)

            if seven_start_dt <= published < seven_end_dt:
                seven_posts += 1
                seven_views += metrics["view_count"]
                seven_likes += metrics["like_count"]
                seven_comments += metrics["comment_count"]
                seven_shares += metrics["share_count"]
                seven_bookmarks += metrics["bookmark_count"]
                if account_key:
                    seven_creators.add(account_key)
                    local_day = published.astimezone(beijing).date().isoformat()
                    if local_day in daily_creator_sets:
                        daily_creator_sets[local_day].add(account_key)

            if yesterday_start_dt <= published < yesterday_end_dt:
                today_posts += 1
                today_views += metrics["view_count"]
                today_likes += metrics["like_count"]
                if account_key:
                    today_creators.add(account_key)

    interactions = seven_likes + seven_comments + seven_shares + seven_bookmarks
    return {
        "product_code": product_code,
        "country_code": country_code or None,
        "source": "museon_clone",
        "today": {
            "creators": len(today_creators),
            "posts": today_posts,
            "views": today_views,
            "likes": today_likes,
            "average_views": round(today_views / today_posts) if today_posts else 0,
            "utc_window": {"start": yesterday_start_dt.isoformat(), "end": yesterday_end_dt.isoformat()},
        },
        "seven_day": {
            "creators": len(seven_creators),
            "posts": seven_posts,
            "views": seven_views,
            "likes": seven_likes,
            "average_creators": sum(len(accounts) for accounts in daily_creator_sets.values()) / 7,
            "average_posts": seven_posts / 7,
            "average_views": round(seven_views / seven_posts) if seven_posts else 0,
            "average_views_per_day": seven_views / 7,
            "average_likes": seven_likes / 7,
            "average_er": (interactions / seven_views * 100) if seven_views else 0,
            "interactions": interactions,
            "utc_window": {"start": seven_start_dt.isoformat(), "end": seven_end_dt.isoformat()},
        },
    }


def query_product_rollups(query):
    rows = query_countries(query)
    product_map = {}
    for row in rows:
        product_code = str(row.get("product_code") or "").upper()
        item = product_map.setdefault(product_code, {
            "product_id": row.get("product_id"),
            "product_code": product_code,
            "product_name": row.get("product_name"),
            "creator_count": 0,
            "material_count": 0,
            "post_count": 0,
            "last_synced_at": "",
            "countries": [],
        })
        country = {
            "country_id": row.get("country_id") or row.get("market_id"),
            "country_code": row.get("country_code") or row.get("market_code"),
            "country_name": row.get("country_name"),
            "creator_count": int(row.get("creator_count") or 0),
            "material_count": int(row.get("material_count") or 0),
            "post_count": int(row.get("post_count") or 0),
            "last_synced_at": row.get("last_synced_at") or "",
        }
        item["countries"].append(country)
        item["creator_count"] += country["creator_count"]
        item["material_count"] += country["material_count"]
        item["post_count"] += country["post_count"]
        if country["last_synced_at"] and country["last_synced_at"] > item["last_synced_at"]:
            item["last_synced_at"] = country["last_synced_at"]
    return list(product_map.values())


def query_museon_clone_product_rollups(query):
    product_filter = query_value(query, "product_code").upper()
    country_filter = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    products = load_data()
    results = []

    for product in products if isinstance(products, list) else []:
        product_code = str(product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
        if product_filter and product_code != product_filter:
            continue
        product_row = {
            "product_id": product.get("id"),
            "product_code": product_code,
            "product_name": product.get("name") or product_code,
            "source": "museon_clone",
            "creator_count": 0,
            "material_count": 0,
            "post_count": 0,
            "last_synced_at": "",
            "countries": [],
        }
        for country in product.get("countries") or []:
            country_code = str(country.get("reelFarmCode") or COUNTRY_CODES.get(country.get("name"), "") or code_from_name(country.get("name"))).upper()
            if country_filter and country_code != country_filter:
                continue
            campaign = museon_clone_campaign(product_code, country_code)
            account_ids = set()
            post_count = 0
            latest = ""
            if campaign:
                posts = museon_all_posts(campaign.get("id"))
                for post in posts:
                    post_count += 1
                    account = museon_account_from_post(post)
                    account_key = normalize_username(account.get("username")) or str(account.get("id") or "")
                    if account_key:
                        account_ids.add(account_key)
                    published_at = museon_post_published_at(post)
                    if published_at and published_at > latest:
                        latest = published_at
            country_row = {
                "country_id": country.get("id"),
                "country_code": country_code,
                "country_name": country.get("name") or country_code,
                "creator_count": len(account_ids),
                "material_count": post_count,
                "post_count": post_count,
                "last_synced_at": latest,
                "campaign_id": campaign.get("id") if campaign else None,
                "campaign_name": (campaign.get("name") or campaign.get("title")) if campaign else None,
            }
            product_row["countries"].append(country_row)
            product_row["creator_count"] += country_row["creator_count"]
            product_row["material_count"] += country_row["material_count"]
            product_row["post_count"] += country_row["post_count"]
            if latest and latest > product_row["last_synced_at"]:
                product_row["last_synced_at"] = latest
        results.append(product_row)
    return results


def previous_complete_windows(now_utc=None):
    beijing = timezone(timedelta(hours=8))
    current_local = (now_utc or datetime.now(timezone.utc)).astimezone(beijing)
    today_start_local = datetime(current_local.year, current_local.month, current_local.day, tzinfo=beijing)
    yesterday_start_local = today_start_local - timedelta(days=1)
    seven_start_local = yesterday_start_local - timedelta(days=6)
    return {
        "yesterday_start": yesterday_start_local.astimezone(timezone.utc).isoformat(),
        "yesterday_end": today_start_local.astimezone(timezone.utc).isoformat(),
        "seven_start": seven_start_local.astimezone(timezone.utc).isoformat(),
        "seven_end": today_start_local.astimezone(timezone.utc).isoformat(),
    }


def named_timezone(name, fallback):
    if ZoneInfo:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    return fallback


def report_timezone():
    return named_timezone(REPORT_TIMEZONE_NAME, BUSINESS_TIMEZONE)


def mixpanel_timezone():
    return named_timezone(MIXPANEL_TIMEZONE_NAME, timezone(timedelta(hours=-7)))


def product_mixpanel_config(product_code):
    code = str(product_code or "").strip().upper()
    return {
        "project_id": (
            os.environ.get(f"MIXPANEL_PROJECT_ID_{code}", "").strip()
            or os.environ.get(f"{code}_MIXPANEL_PROJECT_ID", "").strip()
            or MIXPANEL_PROJECT_ID
        ),
        "username": (
            os.environ.get(f"MIXPANEL_SERVICE_ACCOUNT_USERNAME_{code}", "").strip()
            or os.environ.get(f"{code}_MIXPANEL_SERVICE_ACCOUNT_USERNAME", "").strip()
            or MIXPANEL_SERVICE_ACCOUNT_USERNAME
        ),
        "secret": (
            os.environ.get(f"MIXPANEL_SERVICE_ACCOUNT_SECRET_{code}", "").strip()
            or os.environ.get(f"{code}_MIXPANEL_SERVICE_ACCOUNT_SECRET", "").strip()
            or MIXPANEL_SERVICE_ACCOUNT_SECRET
        ),
        "region": (
            os.environ.get(f"MIXPANEL_REGION_{code}", "").strip().lower()
            or os.environ.get(f"{code}_MIXPANEL_REGION", "").strip().lower()
            or MIXPANEL_REGION
        ),
    }


def product_mixpanel_project_id(product_code):
    return product_mixpanel_config(product_code)["project_id"]


def product_mixpanel_event_name(product_code, event_kind):
    code = str(product_code or "").strip().upper()
    kind = str(event_kind or "").strip().upper()
    default_value = MIXPANEL_ONBOARDING_EVENT if kind == "ONBOARDING" else MIXPANEL_DOWNLOAD_EVENT
    return (
        os.environ.get(f"MIXPANEL_{kind}_EVENT_{code}", "").strip()
        or os.environ.get(f"{code}_MIXPANEL_{kind}_EVENT", "").strip()
        or os.environ.get(f"MIXPANEL_EVENT_{kind}_{code}", "").strip()
        or default_value
    )


def mixpanel_query_base_url(region=None):
    region = (region or MIXPANEL_REGION).strip().lower()
    if region == "eu":
        return "https://eu.mixpanel.com/api/query"
    if region in {"in", "india"}:
        return "https://in.mixpanel.com/api/query"
    return "https://mixpanel.com/api/query"


def mixpanel_export_base_url(region=None):
    region = (region or MIXPANEL_REGION).strip().lower()
    if region == "eu":
        return "https://data-eu.mixpanel.com/api/2.0/export"
    if region in {"in", "india"}:
        return "https://data-in.mixpanel.com/api/2.0/export"
    return "https://data.mixpanel.com/api/2.0/export"


def report_day_window(report_date="", tz=None):
    tz = tz or report_timezone()
    if report_date:
        date_value = datetime.strptime(str(report_date), "%Y-%m-%d").date()
    else:
        current_local = datetime.now(timezone.utc).astimezone(tz)
        date_value = (datetime(current_local.year, current_local.month, current_local.day, tzinfo=tz) - timedelta(days=1)).date()
    start_local = datetime(date_value.year, date_value.month, date_value.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return {
        "report_date": date_value.isoformat(),
        "report_timezone": getattr(tz, "key", REPORT_TIMEZONE_NAME),
        "start_local": start_local,
        "end_local": end_local,
        "utc_start": start_local.astimezone(timezone.utc),
        "utc_end": end_local.astimezone(timezone.utc),
    }


def source_dates_for_utc_window(utc_start, utc_end, source_tz):
    start_source = utc_start.astimezone(source_tz).date()
    end_source = (utc_end - timedelta(microseconds=1)).astimezone(source_tz).date()
    return start_source.isoformat(), end_source.isoformat()


def product_channel_views_for_window(product_code, channel_code, utc_start, utc_end):
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        row = conn.execute(
            f"""
            SELECT
                COUNT(DISTINCT post.id) AS posts,
                COUNT(DISTINCT acc.id) AS creators,
                COALESCE(SUM(post.view_count), 0) AS views,
                COALESCE(SUM(post.like_count), 0) AS likes
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}
              AND post.published_at >= {placeholder}
              AND post.published_at < {placeholder}
              AND post.id IS NOT NULL
            """,
            (channel_code, str(product_code or "").upper(), utc_start.isoformat(), utc_end.isoformat()),
        ).fetchone()
    data = row_dict(row)
    return {
        "posts": int(data.get("posts") or 0),
        "creators": int(data.get("creators") or 0),
        "views": int(data.get("views") or 0),
        "likes": int(data.get("likes") or 0),
    }


def growth_report_windows(days):
    tz = report_timezone()
    current_local = datetime.now(timezone.utc).astimezone(tz)
    today_start = datetime(current_local.year, current_local.month, current_local.day, tzinfo=tz)
    windows = []
    for offset in range(days, 0, -1):
        report_date = (today_start - timedelta(days=offset)).date().isoformat()
        windows.append(report_day_window(report_date, tz))
    return windows


def report_date_for_utc_datetime(value, tz=None):
    tz = tz or report_timezone()
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz).date().isoformat()


def product_channel_daily_views(product_code, channel_code, utc_start, utc_end):
    placeholder = db_placeholder()
    daily = {}
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                post.id AS post_id,
                post.published_at AS published_at,
                COALESCE(post.view_count, 0) AS view_count
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}
              AND post.published_at >= {placeholder}
              AND post.published_at < {placeholder}
              AND post.id IS NOT NULL
            GROUP BY post.id, post.published_at, post.view_count
            """,
            (channel_code, str(product_code or "").upper(), utc_start.isoformat(), utc_end.isoformat()),
        ).fetchall()
    for row in rows:
        item = row_dict(row)
        published_at = parse_iso_datetime(item.get("published_at"))
        report_date = report_date_for_utc_datetime(published_at)
        if not report_date:
            continue
        daily[report_date] = daily.get(report_date, 0) + int(item.get("view_count") or 0)
    return daily


def mixpanel_event_daily_counts(config, event_name, utc_start, utc_end, value_type="general"):
    project_id = (config or {}).get("project_id", "")
    username = (config or {}).get("username", "")
    secret = (config or {}).get("secret", "")
    region = (config or {}).get("region", MIXPANEL_REGION)
    if not project_id or not username or not secret or not event_name:
        return {}
    start_epoch = int(utc_start.timestamp())
    end_epoch = int(utc_end.timestamp())
    source_date_from, source_date_to = source_dates_for_utc_window(utc_start, utc_end, mixpanel_timezone())
    params = urlencode({
        "project_id": project_id,
        "event": json.dumps([event_name], ensure_ascii=False),
        "from_date": source_date_from,
        "to_date": source_date_to,
    })
    credentials = f"{username}:{secret}".encode("utf-8")
    request = Request(
        f"{mixpanel_export_base_url(region)}?{params}",
        headers={
            "Authorization": "Basic " + base64.b64encode(credentials).decode("ascii"),
            "Accept": "text/plain",
        },
    )
    try:
        with urlopen(request, timeout=60, context=make_ssl_context()) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:240]
        raise RuntimeError(f"Mixpanel query failed: {error.code} {detail}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Mixpanel query failed: {error}") from error
    totals = {}
    unique_ids = {}
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        properties = event.get("properties") if isinstance(event, dict) else {}
        if not isinstance(properties, dict):
            properties = {}
        raw_time = properties.get("time", event.get("time") if isinstance(event, dict) else None)
        try:
            timestamp = float(raw_time)
        except (TypeError, ValueError):
            continue
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        if timestamp < start_epoch or timestamp >= end_epoch:
            continue
        report_date = report_date_for_utc_datetime(datetime.fromtimestamp(timestamp, timezone.utc))
        if not report_date:
            continue
        totals[report_date] = totals.get(report_date, 0) + 1
        distinct_id = properties.get("distinct_id") or (event.get("distinct_id") if isinstance(event, dict) else None)
        if distinct_id:
            unique_ids.setdefault(report_date, set()).add(str(distinct_id))
    if value_type == "unique":
        return {report_date: len(ids) for report_date, ids in unique_ids.items()}
    return totals


def mixpanel_event_total(config, event_name, utc_start, utc_end, value_type="general"):
    daily = mixpanel_event_daily_counts(config, event_name, utc_start, utc_end, value_type)
    if not daily and not (config or {}).get("project_id"):
        return None
    return sum(int(value or 0) for value in daily.values())


def sync_product_growth_snapshot(product_code, report_date=""):
    product_code = str(product_code or "").strip().upper()
    if not product_code:
        raise ValueError("product_code is required.")
    window = report_day_window(report_date)
    source_tz = mixpanel_timezone()
    source_date_from, source_date_to = source_dates_for_utc_window(window["utc_start"], window["utc_end"], source_tz)
    rf = product_channel_views_for_window(product_code, "TIKTOK", window["utc_start"], window["utc_end"])
    clone = product_channel_views_for_window(product_code, "MUSEON_CLONE", window["utc_start"], window["utc_end"])
    mixpanel_config = product_mixpanel_config(product_code)
    onboarding_event = product_mixpanel_event_name(product_code, "ONBOARDING")
    onboarding_unique = mixpanel_event_total(mixpanel_config, onboarding_event, window["utc_start"], window["utc_end"], "unique")
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": stable_id("product_daily_growth_snapshot", product_code, window["report_date"]),
        "product_code": product_code,
        "report_date": window["report_date"],
        "report_timezone": window["report_timezone"],
        "source_timezone": getattr(source_tz, "key", MIXPANEL_TIMEZONE_NAME),
        "utc_start": window["utc_start"].isoformat(),
        "utc_end": window["utc_end"].isoformat(),
        "source_date_from": source_date_from,
        "source_date_to": source_date_to,
        "reelfarm_views": rf["views"],
        "clone_views": clone["views"],
        "total_views": rf["views"] + clone["views"],
        "download_count": None,
        "onboarding_unique": onboarding_unique,
        "synced_at": now,
    }
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(conn, "product_daily_growth_snapshots", record, ["product_code", "report_date"])
        conn.commit()
    return record


def sync_product_growth_snapshots(product_code, days=30):
    product_code = str(product_code or "").strip().upper()
    if not product_code:
        raise ValueError("product_code is required.")
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 30
    days = max(1, min(90, days))
    windows = growth_report_windows(days)
    if not windows:
        return []
    overall_utc_start = windows[0]["utc_start"]
    overall_utc_end = windows[-1]["utc_end"]
    source_tz = mixpanel_timezone()
    rf_daily = product_channel_daily_views(product_code, "TIKTOK", overall_utc_start, overall_utc_end)
    clone_daily = product_channel_daily_views(product_code, "MUSEON_CLONE", overall_utc_start, overall_utc_end)
    mixpanel_config = product_mixpanel_config(product_code)
    onboarding_event = product_mixpanel_event_name(product_code, "ONBOARDING")
    onboarding_daily = mixpanel_event_daily_counts(mixpanel_config, onboarding_event, overall_utc_start, overall_utc_end, "unique")
    now = datetime.now(timezone.utc).isoformat()
    records = []
    with connect_db() as conn:
        init_relational_schema(conn)
        for window in windows:
            report_date = window["report_date"]
            source_date_from, source_date_to = source_dates_for_utc_window(window["utc_start"], window["utc_end"], source_tz)
            reelfarm_views = int(rf_daily.get(report_date) or 0)
            clone_views = int(clone_daily.get(report_date) or 0)
            record = {
                "id": stable_id("product_daily_growth_snapshot", product_code, report_date),
                "product_code": product_code,
                "report_date": report_date,
                "report_timezone": window["report_timezone"],
                "source_timezone": getattr(source_tz, "key", MIXPANEL_TIMEZONE_NAME),
                "utc_start": window["utc_start"].isoformat(),
                "utc_end": window["utc_end"].isoformat(),
                "source_date_from": source_date_from,
                "source_date_to": source_date_to,
                "reelfarm_views": reelfarm_views,
                "clone_views": clone_views,
                "total_views": reelfarm_views + clone_views,
                "download_count": None,
                "onboarding_unique": onboarding_daily.get(report_date),
                "synced_at": now,
            }
            upsert_row(conn, "product_daily_growth_snapshots", record, ["product_code", "report_date"])
            records.append(record)
        conn.commit()
    return records


def growth_dashboard_payload(query):
    product_code = query_value(query, "product_code").upper()
    if not product_code:
        raise ValueError("product_code is required.")
    try:
        days = int(query_value(query, "days", 30))
    except ValueError:
        days = 30
    days = max(1, min(180, days))
    tz = report_timezone()
    current_local = datetime.now(timezone.utc).astimezone(tz)
    today_start = datetime(current_local.year, current_local.month, current_local.day, tzinfo=tz)
    date_to = (today_start - timedelta(days=1)).date().isoformat()
    date_from = (today_start - timedelta(days=days)).date().isoformat()
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM product_daily_growth_snapshots
            WHERE product_code = {placeholder}
              AND report_date >= {placeholder}
              AND report_date <= {placeholder}
            ORDER BY report_date
            """,
            (product_code, date_from, date_to),
        ).fetchall()
    data = [row_dict(row) for row in rows]
    latest = data[-1] if data else {}
    return {
        "ok": True,
        "product_code": product_code,
        "report_timezone": REPORT_TIMEZONE_NAME,
        "source_timezone": MIXPANEL_TIMEZONE_NAME,
        "date_from": date_from,
        "date_to": date_to,
        "latest": latest,
        "series": data,
        "totals": {
            "total_views": sum(int(row.get("total_views") or 0) for row in data),
            "reelfarm_views": sum(int(row.get("reelfarm_views") or 0) for row in data),
            "clone_views": sum(int(row.get("clone_views") or 0) for row in data),
            "download_count": sum(int(row.get("download_count") or 0) for row in data if row.get("download_count") is not None),
            "onboarding_unique": sum(int(row.get("onboarding_unique") or 0) for row in data if row.get("onboarding_unique") is not None),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def clean_tag(value):
    tag = re.sub(r"\s+", " ", str(value or "")).strip()
    return tag[:40]


def account_tags_payload(account_ids):
    ids = [str(item or "").strip() for item in account_ids if str(item or "").strip()]
    if not ids:
        return {"ok": True, "tags": {}}
    placeholder = db_placeholder()
    placeholders = ",".join([placeholder] * len(ids))
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"SELECT account_id, tag FROM account_tags WHERE account_id IN ({placeholders}) ORDER BY tag",
            tuple(ids),
        ).fetchall()
    tags = {}
    for row in rows:
        data = row_dict(row)
        tags.setdefault(data.get("account_id"), []).append(data.get("tag"))
    return {"ok": True, "tags": tags}


def account_issues_payload(account_ids):
    ids = [str(item or "").strip() for item in account_ids if str(item or "").strip()]
    if not ids:
        return {"ok": True, "issues": {}}
    placeholder = db_placeholder()
    placeholders = ",".join([placeholder] * len(ids))
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"SELECT account_id, issue FROM account_issues WHERE account_id IN ({placeholders}) ORDER BY issue",
            tuple(ids),
        ).fetchall()
    issues = {}
    for row in rows:
        data = row_dict(row)
        issues.setdefault(data.get("account_id"), []).append(data.get("issue"))
    return {"ok": True, "issues": issues}


def add_account_issue(account_id, issue):
    account_id = str(account_id or "").strip()
    issue = clean_tag(issue)
    if not account_id or not issue:
        raise ValueError("account_id and issue are required.")
    now = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(
            conn,
            "account_issues",
            {
                "id": stable_id("account_issue", account_id, issue.lower()),
                "account_id": account_id,
                "issue": issue,
                "source": "manual",
                "created_at": now,
                "updated_at": now,
            },
            ["account_id", "issue"],
        )
        conn.commit()
    return {"ok": True, "account_id": account_id, "issue": issue}


def delete_account_issue(account_id, issue):
    account_id = str(account_id or "").strip()
    issue = clean_tag(issue)
    if not account_id or not issue:
        raise ValueError("account_id and issue are required.")
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        conn.execute(
            f"DELETE FROM account_issues WHERE account_id = {placeholder} AND issue = {placeholder}",
            (account_id, issue),
        )
        conn.commit()
    return {"ok": True, "account_id": account_id, "issue": issue}


def attach_account_issues(rows):
    ids = [str(row.get("account_id") or "").strip() for row in rows if str(row.get("account_id") or "").strip()]
    issue_map = account_issues_payload(ids).get("issues", {}) if ids else {}
    for row in rows:
        row["issues"] = issue_map.get(row.get("account_id"), [])
    return rows


def product_tags_payload(product_code):
    product_code = str(product_code or "").strip().upper()
    if not product_code:
        raise ValueError("product_code is required.")
    placeholder = db_placeholder()
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
    tags = sorted({
        clean_tag(row_dict(row).get("tag"))
        for row in [*option_rows, *used_rows]
        if clean_tag(row_dict(row).get("tag"))
    }, key=lambda value: value.lower())
    return {"ok": True, "product_code": product_code, "tags": tags}


def create_product_tag(product_code, tag):
    product_code = str(product_code or "").strip().upper()
    tag = clean_tag(tag)
    if not product_code or not tag:
        raise ValueError("product_code and tag are required.")
    now = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(
            conn,
            "product_tags",
            {"id": stable_id("product_tag", product_code, tag.lower()), "product_code": product_code, "tag": tag, "created_at": now},
            ["product_code", "tag"],
        )
        conn.commit()
    return product_tags_payload(product_code)


def add_account_tag(account_id, tag):
    account_id = str(account_id or "").strip()
    tag = clean_tag(tag)
    if not account_id or not tag:
        raise ValueError("account_id and tag are required.")
    now = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(
            conn,
            "account_tags",
            {"id": stable_id("account_tag", account_id, tag.lower()), "account_id": account_id, "tag": tag, "created_at": now},
            ["account_id", "tag"],
        )
        conn.commit()
    return {"ok": True, "account_id": account_id, "tag": tag}


def delete_account_tag(account_id, tag):
    account_id = str(account_id or "").strip()
    tag = clean_tag(tag)
    if not account_id or not tag:
        raise ValueError("account_id and tag are required.")
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        conn.execute(f"DELETE FROM account_tags WHERE account_id = {placeholder} AND tag = {placeholder}", (account_id, tag))
        conn.commit()
    return {"ok": True, "account_id": account_id, "tag": tag}


_MUSEON_CAMPAIGN_CACHE = {"loaded_at": 0, "campaigns": []}


def museon_request(path, params=None):
    if not MUSEON_API_KEY:
        raise RuntimeError("MUSEON_API_KEY is not configured.")
    clean_path = "/" + str(path or "").lstrip("/")
    query = urlencode(params or {}, doseq=True)
    url = f"{MUSEON_BASE_URL}{clean_path}" + (f"?{query}" if query else "")
    request = Request(url, headers={
        "X-API-KEY": MUSEON_API_KEY,
        "Accept": "application/json",
        "User-Agent": MUSEON_USER_AGENT,
    })
    try:
        with urlopen(request, timeout=20, context=make_ssl_context()) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Museon returned HTTP {exc.code}: {detail[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Museon API: {exc.reason}") from exc

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError("Museon returned a non-JSON response.") from exc
    if isinstance(payload, dict) and payload.get("error"):
        error = payload.get("error") or {}
        raise RuntimeError(error.get("message") or error.get("code") or "Museon API error")
    return payload


def museon_list_payload(payload):
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        if isinstance(payload.get("items"), list):
            return payload["items"]
    return payload if isinstance(payload, list) else []


def museon_campaigns(force=False):
    now = time.time()
    if not force and _MUSEON_CAMPAIGN_CACHE["campaigns"] and now - _MUSEON_CAMPAIGN_CACHE["loaded_at"] < 300:
        return _MUSEON_CAMPAIGN_CACHE["campaigns"]

    campaigns = []
    page = 1
    while page <= 20:
        payload = museon_request(
            "/campaigns",
            {"workspace_id": MUSEON_WORKSPACE_ID, "page": page, "page_size": 100},
        )
        items = museon_list_payload(payload)
        campaigns.extend([item for item in items if isinstance(item, dict)])
        pagination = payload.get("pagination") if isinstance(payload, dict) else {}
        total = int((pagination or {}).get("total") or 0)
        if not items or (total and len(campaigns) >= total):
            break
        page += 1

    _MUSEON_CAMPAIGN_CACHE["campaigns"] = campaigns
    _MUSEON_CAMPAIGN_CACHE["loaded_at"] = now
    return campaigns


def museon_clone_campaign(product_code, country_code):
    product_code = str(product_code or "").strip().upper()
    country_code = str(country_code or "").strip().upper()
    if not product_code or not country_code:
        return None
    exact_names = {
        f"{country_code}-{product_code}-CLONE",
        f"{product_code}-{country_code}-CLONE",
        f"{country_code}_{product_code}_CLONE",
        f"{product_code}_{country_code}_CLONE",
    }
    fallback = None
    for campaign in museon_campaigns():
        name = str(campaign.get("name") or campaign.get("title") or "").strip()
        upper_name = name.upper()
        tokens = {token for token in re.split(r"[^A-Z0-9]+", upper_name) if token}
        if upper_name in exact_names:
            return campaign
        if "CLONE" in tokens and product_code in tokens and country_code in tokens:
            fallback = fallback or campaign
    return fallback


def museon_clone_campaigns_for_product(product_code, country_code=""):
    product_code = str(product_code or "").strip().upper()
    country_code = str(country_code or "").strip().upper()
    if not product_code:
        return []
    if country_code:
        campaign = museon_clone_campaign(product_code, country_code)
        return [{"country_code": country_code, "campaign": campaign}] if campaign else []

    contexts = []
    products = load_data()
    for product in products if isinstance(products, list) else []:
        code = str(product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
        if code != product_code:
            continue
        for country in product.get("countries") or []:
            ccode = str(country.get("reelFarmCode") or COUNTRY_CODES.get(country.get("name"), "") or code_from_name(country.get("name"))).upper()
            campaign = museon_clone_campaign(product_code, ccode)
            if campaign:
                contexts.append({"country_code": ccode, "campaign": campaign})
        break
    return contexts


def museon_pagination_total(payload, fallback_count=0):
    if isinstance(payload, dict):
        pagination = payload.get("pagination") or payload.get("meta") or {}
        for key in ("total", "total_count", "count"):
            if isinstance(pagination, dict) and pagination.get(key) is not None:
                try:
                    return int(pagination.get(key) or 0)
                except (TypeError, ValueError):
                    pass
    return fallback_count


def museon_posts(campaign_id, date_from="", date_to="", username="", page=1, page_size=100, sort=""):
    params = {"page": page, "page_size": page_size}
    if sort:
        params["sort"] = sort
    if username:
        params["username"] = username
    if date_from:
        params["published_after"] = post_datetime_bound(date_from)
    if date_to:
        params["published_before"] = post_datetime_bound(date_to, end=True)
    payload = museon_request(f"/campaigns/{quote(str(campaign_id), safe='')}/posts", params)
    return museon_list_payload(payload), museon_pagination_total(payload)


def museon_all_posts(campaign_id, date_from="", date_to="", max_pages=40):
    posts = []
    page = 1
    total = 0
    while True:
        if max_pages and page > max_pages:
            break
        items, total = museon_posts(campaign_id, date_from, date_to, page=page, page_size=100)
        posts.extend([item for item in items if isinstance(item, dict)])
        if not items or (total and len(posts) >= total):
            break
        page += 1
    return posts


def local_product_country_context(product_code, country_code):
    products = load_data()
    product_context = {"id": None, "code": product_code, "name": product_code}
    country_context = {"id": None, "code": country_code, "name": country_code}
    for product in products if isinstance(products, list) else []:
        code = str(product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
        if code != product_code:
            continue
        product_context = {"id": product.get("id"), "code": code, "name": product.get("name") or product_code}
        for country in product.get("countries") or []:
            ccode = str(country.get("reelFarmCode") or COUNTRY_CODES.get(country.get("name"), "") or code_from_name(country.get("name"))).upper()
            if ccode == country_code:
                country_context = {"id": country.get("id"), "code": ccode, "name": country.get("name") or country_code}
                break
        break
    return product_context, country_context


def reelfarm_account_lookup(product_code, country_code):
    lookup = {}
    query = {"product_code": [product_code], "country_code": [country_code]}
    for row in query_reelfarm_accounts(query):
        username = normalize_username(row.get("username") or row.get("display_name"))
        if username:
            lookup[username] = row
    return lookup


def museon_account_from_post(post):
    account = post.get("account") if isinstance(post.get("account"), dict) else {}
    username = account.get("username") or post.get("username") or post.get("account_username")
    return {
        "id": account.get("id") or post.get("creator_id") or post.get("account_id") or username,
        "username": username,
        "display_name": account.get("display_name") or account.get("name") or username,
        "avatar_url": account.get("avatar_url") or account.get("image_url") or account.get("profile_image_url"),
        "status": account.get("status") or post.get("status") or "active",
        "category_tags": account.get("category_tags") or [],
    }


def museon_post_metrics(post):
    metrics = post.get("metrics") if isinstance(post.get("metrics"), dict) else {}
    return {
        "view_count": int(metrics.get("views") or metrics.get("view_count") or post.get("views") or 0),
        "like_count": int(metrics.get("likes") or metrics.get("like_count") or post.get("likes") or 0),
        "comment_count": int(metrics.get("comments") or metrics.get("comment_count") or post.get("comments") or 0),
        "share_count": int(metrics.get("shares") or metrics.get("share_count") or post.get("shares") or 0),
        "bookmark_count": int(metrics.get("saves") or metrics.get("bookmark_count") or metrics.get("bookmarks") or 0),
    }


def normalize_image_entries(values):
    images = []
    for item in values or []:
        if isinstance(item, str):
            url = item
        elif isinstance(item, dict):
            url = item.get("image_url") or item.get("url") or item.get("src") or item.get("download_url")
        else:
            url = ""
        if url:
            images.append({"image_url": url})

    seen = set()
    deduped = []
    for image in images:
        url = image.get("image_url")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(image)
    return deduped


def museon_post_images(post):
    candidates = [
        post.get("slideshow_images"),
        post.get("images"),
        post.get("media_urls"),
        post.get("image_urls"),
    ]
    content = post.get("content") if isinstance(post.get("content"), dict) else {}
    candidates.extend([
        content.get("slideshow_images"),
        content.get("images"),
        content.get("media_urls"),
        content.get("image_urls"),
    ])

    images = []
    for candidate in candidates:
        if isinstance(candidate, list):
            images.extend(candidate)
    return normalize_image_entries(images)


def museon_content_download_images(content_id):
    if not content_id:
        return []
    try:
        payload = museon_request(f"/content/{quote(str(content_id), safe='')}/download-urls")
    except RuntimeError:
        return []
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return []
    values = []
    for key in ("download_urls", "image_urls", "media_urls"):
        if isinstance(data.get(key), list):
            values.extend(data.get(key) or [])
    if data.get("thumbnail_url"):
        values.append(data.get("thumbnail_url"))
    return normalize_image_entries(values)


def local_product_country_record(product_id="", country_id="", product_code="", country_code=""):
    product_code = str(product_code or "").strip().upper()
    country_code = str(country_code or "").strip().upper()
    for product in load_data():
        if not isinstance(product, dict):
            continue
        pcode = str(product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
        if product_id and str(product.get("id") or "") != str(product_id):
            continue
        if product_code and pcode != product_code:
            continue
        for country in product.get("countries") or []:
            if not isinstance(country, dict):
                continue
            ccode = str(country.get("reelFarmCode") or COUNTRY_CODES.get(country.get("name"), "") or code_from_name(country.get("name"))).upper()
            if country_id and str(country.get("id") or "") != str(country_id):
                continue
            if country_code and ccode != country_code:
                continue
            return product, country, pcode, ccode
    return (
        {
            "id": product_id or stable_id("product", product_code),
            "name": product_code or "Product",
            "reelFarmCode": product_code,
            "folder": "",
            "logo": "",
        },
        {
            "id": country_id or stable_id("country", country_code),
            "name": country_code or "Country",
            "reelFarmCode": country_code,
        },
        product_code,
        country_code,
    )


def sync_museon_clone_country(product_id="", country_id="", product_code="", country_code=""):
    product, country, product_code, country_code = local_product_country_record(product_id, country_id, product_code, country_code)
    if not product_code or not country_code:
        raise ValueError("Missing product_code or country_code.")

    started = time.perf_counter()
    synced_at = datetime.now(timezone.utc).isoformat()
    campaign = museon_clone_campaign(product_code, country_code)
    if not campaign:
        return {
            "ok": True,
            "skipped": True,
            "source": "museon_clone",
            "product_code": product_code,
            "country_code": country_code,
            "creator_count": 0,
            "material_count": 0,
            "post_count": 0,
            "synced_at": synced_at,
            "message": f"No Museon clone campaign found for {country_code}-{product_code}.",
        }

    posts = museon_all_posts(campaign.get("id"), max_pages=0)
    channel_id = stable_id("channel", "MUSEON_CLONE")
    product_row_id = str(product.get("id") or stable_id("product", product_code))
    market_id = stable_id("market", country_code)
    product_market_id = stable_id("product_market", product_row_id, market_id)
    product_market_channel_id = stable_id("product_market_channel", product_market_id, channel_id)
    campaign_name = str(campaign.get("name") or campaign.get("title") or f"{country_code}-{product_code}-Clone")
    campaign_id = str(campaign.get("id") or stable_id("museon_campaign", campaign_name))
    account_ids = set()
    material_count = 0
    post_count = 0
    download_image_cache = {}

    with connect_db() as conn:
        init_relational_schema(conn)
        zero_play_candidates = {}
        upsert_row(conn, "channels", {"id": channel_id, "name": "Clone Slide Show", "code": "MUSEON_CLONE"}, ["code"])
        upsert_row(
            conn,
            "products",
            {
                "id": product_row_id,
                "name": str(product.get("name") or product_code),
                "code": product_code,
                "owner_type": product.get("folder") or product.get("owner_type") or "",
                "logo_url": product.get("logo") or product.get("logo_url") or "",
                "created_at": product.get("created_at") or synced_at,
                "updated_at": synced_at,
            },
            ["id"],
        )
        upsert_row(conn, "markets", {"id": market_id, "name": str(country.get("name") or country_code), "code": country_code}, ["code"])
        upsert_row(conn, "product_markets", {"id": product_market_id, "product_id": product_row_id, "market_id": market_id}, ["product_id", "market_id"])
        upsert_row(
            conn,
            "product_market_channels",
            {"id": product_market_channel_id, "product_market_id": product_market_id, "channel_id": channel_id},
            ["product_market_id", "channel_id"],
        )

        for post in posts:
            if not isinstance(post, dict):
                continue
            account = museon_account_from_post(post)
            username = normalize_username(account.get("username")) or normalize_username(account.get("display_name"))
            if not username:
                continue
            museon_account_id = str(account.get("id") or username)
            account_source_id = f"museon:{museon_account_id}"
            account_id = stable_id("museon_account", product_market_channel_id, account_source_id)
            automation_source_id = f"museon:{campaign_id}:{museon_account_id}"
            automation_id = stable_id("museon_automation", automation_source_id)
            post_source_id = str(post.get("id") or post.get("post_id") or post.get("content_id") or stable_id("museon_post_source", campaign_id, username, museon_post_published_at(post)))
            material_source_id = str(post.get("content_id") or post_source_id)
            reelfarm_video_id = f"museon:{campaign_id}:{material_source_id}"
            reelfarm_post_id = f"museon:{campaign_id}:{post_source_id}"
            material_id = stable_id("museon_material", reelfarm_video_id)
            post_id = stable_id("museon_post", reelfarm_post_id)
            metrics = museon_post_metrics(post)
            published_at = museon_post_published_at(post)
            images = museon_post_images(post)
            if not images and material_source_id:
                if material_source_id not in download_image_cache:
                    download_image_cache[material_source_id] = museon_content_download_images(material_source_id)
                images = download_image_cache.get(material_source_id) or []

            account_ids.add(account_id)
            material_count += 1
            post_count += 1
            zero_play_candidates.setdefault(account_id, [])
            collect_zero_play_issue_candidate(
                zero_play_candidates,
                account_id,
                published_at,
                metrics["view_count"],
                business_date_string(synced_at),
            )

            upsert_row(
                conn,
                "accounts",
                {
                    "id": account_id,
                    "product_market_channel_id": product_market_channel_id,
                    "reelfarm_account_id": account_source_id,
                    "username": account.get("username") or username,
                    "display_name": account.get("display_name") or account.get("username") or username,
                    "avatar_url": account.get("avatar_url") or "",
                    "status": account.get("status") or "active",
                },
                ["product_market_channel_id", "reelfarm_account_id"],
            )
            upsert_row(
                conn,
                "automations",
                {
                    "id": automation_id,
                    "product_market_channel_id": product_market_channel_id,
                    "account_id": account_id,
                    "reelfarm_automation_id": automation_source_id,
                    "name": campaign_name,
                    "status": "active",
                    "schedule": "[]",
                    "settings_json": db_json({"source": "museon_clone", "campaign": campaign, "account": account}),
                    "post_mode": "RPA",
                    "publish_method": "rpa",
                    "created_at": campaign.get("created_at") or "",
                    "synced_at": synced_at,
                },
                ["reelfarm_automation_id"],
            )
            upsert_row(
                conn,
                "materials",
                {
                    "id": material_id,
                    "automation_id": automation_id,
                    "product_market_channel_id": product_market_channel_id,
                    "account_id": account_id,
                    "concept_id": None,
                    "format_id": None,
                    "reelfarm_video_id": reelfarm_video_id,
                    "video_type": post.get("content_type") or "slideshow",
                    "hook": post.get("title") or post.get("description") or "",
                    "prompt": post.get("caption") or post.get("description") or "",
                    "images_json": db_json(images),
                    "slide_count": int_or_none(post.get("slide_count")) or len(images),
                    "status": post.get("status") or "",
                    "created_at": post.get("created_at") or published_at or "",
                    "finished_at": post.get("finished_at") or "",
                    "synced_at": synced_at,
                },
                ["reelfarm_video_id"],
            )
            upsert_row(
                conn,
                "posts",
                {
                    "id": post_id,
                    "material_id": material_id,
                    "account_id": account_id,
                    "reelfarm_post_id": reelfarm_post_id,
                    "status": post.get("status") or "",
                    "title": post.get("title") or post.get("description") or "",
                    "published_at": published_at,
                    "published_at_readable": readable_utc_datetime(published_at),
                    "view_count": metrics["view_count"],
                    "like_count": metrics["like_count"],
                    "comment_count": metrics["comment_count"],
                    "share_count": metrics["share_count"],
                    "bookmark_count": metrics["bookmark_count"],
                    "synced_at": synced_at,
                },
                ["reelfarm_post_id"],
            )
            snapshot_date = utc_snapshot_date()
            upsert_row(
                conn,
                "post_daily_snapshots",
                {
                    "id": stable_id("post_daily_snapshot", post_id, snapshot_date),
                    "post_id": post_id,
                    "snapshot_date": snapshot_date,
                    "view_count": metrics["view_count"],
                    "like_count": metrics["like_count"],
                    "comment_count": metrics["comment_count"],
                    "share_count": metrics["share_count"],
                    "bookmark_count": metrics["bookmark_count"],
                    "synced_at": synced_at,
                },
                ["post_id", "snapshot_date"],
            )
        apply_zero_play_issues(conn, zero_play_candidates, synced_at)
        conn.commit()

    return {
        "ok": True,
        "source": "museon_clone",
        "product_code": product_code,
        "country_code": country_code,
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "creator_count": len(account_ids),
        "material_count": material_count,
        "post_count": post_count,
        "synced_at": synced_at,
        "duration_total_seconds": round(time.perf_counter() - started, 3),
    }


def query_museon_clone_accounts(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if not date_from and not date_to:
        date_from, date_to = query_days_window(query)
    campaign = museon_clone_campaign(product_code, country_code)
    if not campaign:
        return []

    campaign_id = campaign.get("id")
    posts = museon_all_posts(campaign_id, date_from, date_to)
    grouped = {}
    for post in posts:
        account = museon_account_from_post(post)
        username_key = normalize_username(account.get("username"))
        if not username_key:
            continue
        row = grouped.setdefault(username_key, {
            "account": account,
            "posts": 0,
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "bookmarks": 0,
            "latest_post_at": "",
        })
        row["posts"] += 1
        metrics = museon_post_metrics(post)
        row["views"] += metrics["view_count"]
        row["likes"] += metrics["like_count"]
        row["comments"] += metrics["comment_count"]
        row["shares"] += metrics["share_count"]
        row["bookmarks"] += metrics["bookmark_count"]
        published_at = post.get("published_at") or post.get("created_at") or ""
        if published_at and published_at > row["latest_post_at"]:
            row["latest_post_at"] = published_at

    rows = []
    for username_key, grouped_row in grouped.items():
        account = grouped_row["account"]
        synthetic_id = f"museon:{product_code}:{country_code}:{username_key}"
        rows.append({
            "account_id": synthetic_id,
            "reelfarm_account_id": None,
            "museon_account_id": account.get("id"),
            "username": account.get("username"),
            "display_name": account.get("display_name") or account.get("username"),
            "avatar_url": account.get("avatar_url"),
            "status": campaign.get("status") or "active",
            "automation_count": 1,
            "automation_name": campaign.get("name") or campaign.get("title"),
            "automation_names": campaign.get("name") or campaign.get("title"),
            "publish_method": "rpa",
            "material_count": grouped_row["posts"],
            "post_count": grouped_row["posts"],
            "total_views": grouped_row["views"],
            "total_likes": grouped_row["likes"],
            "total_comments": grouped_row["comments"],
            "total_shares": grouped_row["shares"],
            "total_bookmarks": grouped_row["bookmarks"],
            "latest_post_at": grouped_row["latest_post_at"],
            "last_synced_at": grouped_row["latest_post_at"],
            "data_source": "museon_clone",
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name") or campaign.get("title"),
        })
    return attach_account_issues(sorted(rows, key=lambda row: (int(row.get("total_views") or 0), int(row.get("post_count") or 0)), reverse=True))


def reelfarm_detailed_rows_for_username(product_code, country_code, username):
    username_key = normalize_username(username)
    if not username_key:
        return []
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT {detailed_select()}
            {relational_base_from()}
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}
              AND m.code = {placeholder}
              AND LOWER(REPLACE(acc.username, '@', '')) = {placeholder}
              AND post.id IS NOT NULL
            ORDER BY post.published_at DESC
            LIMIT 500
            """,
            ("TIKTOK", product_code, country_code, username_key),
        ).fetchall()
    return [detailed_row(row) for row in rows]


def nearest_reelfarm_row(museon_post, rf_rows):
    published = parse_iso_datetime(museon_post.get("published_at"))
    if not published:
        return None
    best = None
    best_delta = 10**9
    for row in rf_rows:
        candidate = parse_iso_datetime((row.get("post") or {}).get("published_at"))
        if not candidate:
            continue
        delta = abs((candidate - published).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best = row
    return best if best and best_delta <= 15 * 60 else None


def museon_post_to_detailed_row(post, product, country, rf_match=None):
    account = museon_account_from_post(post)
    metrics = museon_post_metrics(post)
    published_at = post.get("published_at") or post.get("created_at") or ""
    content_id = post.get("content_id") or post.get("id")
    images = museon_post_images(post)
    if not images and content_id:
        images = museon_content_download_images(content_id)
    base = rf_match or {
        "product": product,
        "country": country,
        "market": country,
        "account": {},
        "automation": {},
        "material": {},
        "post": {},
        "metrics": {},
    }
    material = dict(base.get("material") or {})
    material.update({
        "id": material.get("id") or post.get("content_id") or post.get("id"),
        "reelfarm_video_id": material.get("reelfarm_video_id") or post.get("content_id"),
        "video_type": material.get("video_type") or post.get("content_type") or "slideshow",
        "hook": material.get("hook") or post.get("title") or post.get("description"),
        "prompt": material.get("prompt") or post.get("description"),
        "slideshow_images": material.get("slideshow_images") or images,
        "slide_count": material.get("slide_count") or len(images),
        "status": material.get("status") or post.get("status"),
    })
    return {
        "product": product,
        "country": country,
        "market": country,
        "account": {
            "id": (base.get("account") or {}).get("id") or f"museon:{product.get('code')}:{country.get('code')}:{normalize_username(account.get('username'))}",
            "reelfarm_account_id": (base.get("account") or {}).get("reelfarm_account_id"),
            "museon_account_id": account.get("id"),
            "username": account.get("username"),
            "display_name": account.get("display_name"),
            "avatar_url": account.get("avatar_url") or (base.get("account") or {}).get("avatar_url"),
            "status": account.get("status"),
        },
        "automation": base.get("automation") or {},
        "material": material,
        "post": {
            "id": post.get("id"),
            "reelfarm_post_id": (base.get("post") or {}).get("reelfarm_post_id"),
            "museon_post_id": post.get("id"),
            "status": post.get("status"),
            "title": post.get("title") or post.get("description"),
            "published_at": published_at,
            "published_at_readable": readable_utc_datetime(published_at),
            "synced_at": post.get("synced_at") or post.get("updated_at"),
        },
        "metrics": metrics,
    }


def query_museon_clone_account_posts(query):
    product_code = query_value(query, "product_code").upper()
    country_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    account_id = query_value(query, "account_id")
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if not date_from and not date_to:
        date_from, date_to = query_days_window(query)
    limit, offset = query_limit_offset(query)
    campaign = museon_clone_campaign(product_code, country_code)
    if not campaign:
        return [], pagination_payload(limit, offset, [], 0)
    username = account_id
    if account_id.startswith("museon:"):
        username = account_id.split(":")[-1]
    page = (offset // limit) + 1
    posts, total = museon_posts(campaign.get("id"), date_from, date_to, username=username, page=page, page_size=limit)
    product, country = local_product_country_context(product_code, country_code)
    rows = []
    for post in posts:
        rows.append(museon_post_to_detailed_row(post, product, country))
    return rows, pagination_payload(limit, offset, rows, total)


def query_reelfarm_accounts(query):
    where_sql, params = common_where(query, include_post_dates=False)
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if not date_from and not date_to:
        date_from, date_to = query_days_window(query)
    metric_condition = "1 = 1"
    metric_params = []
    placeholder = db_placeholder()
    if date_from:
        metric_condition += f" AND post.published_at >= {placeholder}"
        metric_params.append(post_datetime_bound(date_from))
    if date_to:
        metric_condition += f" AND post.published_at <= {placeholder}"
        metric_params.append(post_datetime_bound(date_to, end=True))
    metric_condition_count = 8
    automation_names_sql = (
        "STRING_AGG(DISTINCT a.name, ' | ')"
        if using_postgres()
        else "GROUP_CONCAT(DISTINCT a.name)"
    )
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
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
                COUNT(DISTINCT CASE WHEN {metric_condition} THEN mat.id END) AS material_count,
                COUNT(DISTINCT CASE WHEN {metric_condition} THEN post.id END) AS post_count,
                COALESCE(SUM(CASE WHEN {metric_condition} THEN post.view_count ELSE 0 END), 0) AS total_views,
                COALESCE(SUM(CASE WHEN {metric_condition} THEN post.like_count ELSE 0 END), 0) AS total_likes,
                COALESCE(SUM(CASE WHEN {metric_condition} THEN post.comment_count ELSE 0 END), 0) AS total_comments,
                COALESCE(SUM(CASE WHEN {metric_condition} THEN post.share_count ELSE 0 END), 0) AS total_shares,
                COALESCE(SUM(CASE WHEN {metric_condition} THEN post.bookmark_count ELSE 0 END), 0) AS total_bookmarks,
                MAX(CASE WHEN {metric_condition} THEN post.published_at END) AS latest_post_at,
                MAX(COALESCE(post.synced_at, mat.synced_at, a.synced_at)) AS last_synced_at
            {relational_base_from()}
            WHERE {where_sql} AND acc.id IS NOT NULL
            GROUP BY acc.id, acc.reelfarm_account_id, acc.username, acc.display_name, acc.avatar_url
            ORDER BY total_views DESC, post_count DESC
            """,
            tuple(metric_params * metric_condition_count + params),
        ).fetchall()
    return [row_dict(row) for row in rows]


def query_accounts(query):
    if query_value(query, "source").strip().lower() in {"museon_clone", "clone", "museon"}:
        return query_museon_clone_accounts(query)
    return query_reelfarm_accounts(query)


def beijing_day_window(now=None):
    beijing = timezone(timedelta(hours=8))
    current = now or datetime.now(timezone.utc)
    local = current.astimezone(beijing)
    start_local = datetime(local.year, local.month, local.day, tzinfo=beijing)
    end_local = start_local + timedelta(days=1)
    return {
        "beijing_date": start_local.date().isoformat(),
        "utc_start": start_local.astimezone(timezone.utc).isoformat(),
        "utc_end": end_local.astimezone(timezone.utc).isoformat(),
    }


def product_country_lookup():
    products = load_data()
    lookup = {}
    for product in products if isinstance(products, list) else []:
        if not isinstance(product, dict):
            continue
        product_id = str(product.get("id") or "")
        product_code = str(product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
        for country in product.get("countries") or []:
            if not isinstance(country, dict):
                continue
            country_id = str(country.get("id") or "")
            country_code = str(country.get("reelFarmCode") or COUNTRY_CODES.get(country.get("name"), "") or code_from_name(country.get("name"))).upper()
            lookup[(product_id, country_id)] = {
                "product": {
                    "id": product_id,
                    "name": product.get("name") or "",
                    "code": product_code,
                    "folder": product.get("folder") or product.get("owner_type") or "",
                },
                "country": {
                    "id": country_id,
                    "name": country.get("name") or "",
                    "code": country_code,
                },
            }
    return lookup


def publish_check_accounts(product_code, country_code, utc_start, utc_end):
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                acc.id AS account_id,
                acc.reelfarm_account_id,
                acc.username,
                acc.display_name,
                acc.avatar_url,
                acc.status AS account_status,
                a.id AS automation_id,
                a.reelfarm_automation_id,
                a.name AS automation_name,
                a.status AS automation_status,
                COUNT(DISTINCT CASE
                    WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder}
                    THEN post.id
                END) AS published_count,
                MAX(CASE
                    WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder}
                    THEN post.published_at
                END) AS today_latest_post_at,
                MAX(post.published_at) AS latest_post_at
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            JOIN automations a ON a.product_market_channel_id = pmc.id
            LEFT JOIN accounts acc ON acc.id = a.account_id
            LEFT JOIN materials mat ON mat.automation_id = a.id
            LEFT JOIN posts post ON post.material_id = mat.id
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}
              AND m.code = {placeholder}
              AND acc.id IS NOT NULL
            GROUP BY
                acc.id,
                acc.reelfarm_account_id,
                acc.username,
                acc.display_name,
                acc.avatar_url,
                acc.status,
                a.id,
                a.reelfarm_automation_id,
                a.name,
                a.status
            ORDER BY acc.username, a.name
            """,
            (utc_start, utc_end, utc_start, utc_end, "TIKTOK", product_code, country_code),
        ).fetchall()
    return [row_dict(row) for row in rows]


def run_publish_check():
    state = load_publish_check_state()
    window = beijing_day_window()
    lookup = product_country_lookup()
    groups = []
    totals = {
        "assignments": 0,
        "accounts": 0,
        "published_accounts": 0,
        "missing_accounts": 0,
    }

    for assignment in state.get("assignments", []):
        product_id = str(assignment.get("product_id") or "")
        country_id = str(assignment.get("country_id") or "")
        context = lookup.get((product_id, country_id))
        if not context:
            continue

        product_code = context["product"]["code"]
        country_code = context["country"]["code"]
        accounts = publish_check_accounts(product_code, country_code, window["utc_start"], window["utc_end"])
        missing = [account for account in accounts if int(account.get("published_count") or 0) <= 0]
        published_count = len(accounts) - len(missing)
        group = {
            "assignment_id": assignment.get("id"),
            "person_id": assignment.get("person_id"),
            "person_name": assignment.get("person_name") or "未命名负责人",
            "product": context["product"],
            "country": context["country"],
            "account_count": len(accounts),
            "published_account_count": published_count,
            "missing_account_count": len(missing),
            "missing_accounts": missing,
        }
        groups.append(group)
        totals["assignments"] += 1
        totals["accounts"] += len(accounts)
        totals["published_accounts"] += published_count
        totals["missing_accounts"] += len(missing)

    result = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "beijing_date": window["beijing_date"],
        "utc_window": {"start": window["utc_start"], "end": window["utc_end"]},
        "totals": totals,
        "groups": groups,
    }
    state["last_result"] = result
    save_publish_check_state(state)
    return result


def publish_check_reminder_text(result):
    totals = result.get("totals") if isinstance(result, dict) else {}
    groups = result.get("groups") if isinstance(result, dict) else []
    missing_total = int((totals or {}).get("missing_accounts") or 0)
    beijing_date = result.get("beijing_date") or "未生成日期"
    lines = [
        f"Deca Growth 发布检查提醒",
        f"北京时间日期：{beijing_date}",
        f"未发布账号：{missing_total}",
        "",
    ]
    if missing_total <= 0:
        lines.append("全部负责范围今天都有发布。")
        return "\n".join(lines)

    shown = 0
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, dict):
            continue
        missing_count = int(group.get("missing_account_count") or 0)
        if missing_count <= 0:
            continue
        product = group.get("product") if isinstance(group.get("product"), dict) else {}
        country = group.get("country") if isinstance(group.get("country"), dict) else {}
        lines.append(f"{group.get('person_name') or '未命名负责人'}｜{product.get('name') or '-'} · {country.get('name') or '-'}：{missing_count} 个账号未发布")
        for account in (group.get("missing_accounts") or [])[:8]:
            if not isinstance(account, dict):
                continue
            username = account.get("username") or account.get("display_name") or account.get("reelfarm_account_id") or account.get("account_id") or "unknown"
            automation = account.get("automation_name") or account.get("reelfarm_automation_id") or "无 automation 名称"
            lines.append(f"  - @{str(username).lstrip('@')}｜{automation}")
            shown += 1
        if missing_count > 8:
            lines.append(f"  - 还有 {missing_count - 8} 个账号未展示")
        lines.append("")
        if shown >= 40:
            lines.append("更多未发布账号请打开中台查看。")
            break
    return "\n".join(lines).strip()


def feishu_signed_payload(message):
    payload = {
        "msg_type": "text",
        "content": {"text": message},
    }
    if FEISHU_WEBHOOK_SECRET:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{FEISHU_WEBHOOK_SECRET}"
        sign = base64.b64encode(hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()).decode("utf-8")
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    return payload


def send_feishu_message(message):
    if not FEISHU_WEBHOOK_URL:
        return {"ok": False, "error": "FEISHU_WEBHOOK_URL is not configured."}
    body = json.dumps(feishu_signed_payload(message), ensure_ascii=False).encode("utf-8")
    request = Request(
        FEISHU_WEBHOOK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=12, context=make_ssl_context()) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"Feishu returned HTTP {exc.code}: {detail[:300]}"}
    except URLError as exc:
        return {"ok": False, "error": f"Could not reach Feishu webhook: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": f"Feishu send failed: {exc}"}

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"raw": raw}
    code = payload.get("code", payload.get("StatusCode", 0))
    if code not in (0, "0", None):
        return {"ok": False, "error": payload.get("msg") or payload.get("StatusMessage") or raw[:300], "response": payload}
    return {"ok": True, "response": payload}


def send_publish_check_reminder():
    state = load_publish_check_state()
    result = state.get("last_result") if isinstance(state, dict) else None
    if not isinstance(result, dict):
        return {"ok": False, "error": "No publish check result yet. Run check first."}
    message = publish_check_reminder_text(result)
    sent = send_feishu_message(message)
    if not sent.get("ok"):
        return sent
    return {
        "ok": True,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "missing_accounts": (result.get("totals") or {}).get("missing_accounts", 0),
        "message_preview": message[:500],
    }


def detailed_select():
    return """
        p.id AS product_id,
        p.code AS product_code,
        p.name AS product_name,
        m.id AS market_id,
        m.code AS market_code,
        m.name AS market_name,
        acc.id AS account_id,
        acc.reelfarm_account_id,
        acc.username AS account_username,
        acc.display_name AS account_display_name,
        acc.avatar_url AS account_avatar_url,
        acc.status AS account_status,
        a.id AS automation_id,
        a.reelfarm_automation_id,
        a.name AS automation_name,
        a.status AS automation_status,
        a.schedule AS automation_schedule,
        mat.id AS material_id,
        mat.reelfarm_video_id,
        mat.video_type,
        mat.hook,
        mat.prompt,
        mat.images_json,
        mat.slide_count,
        mat.status AS material_status,
        mat.created_at AS material_created_at,
        mat.finished_at AS material_finished_at,
        post.id AS post_id,
        post.reelfarm_post_id,
        post.status AS post_status,
        post.title AS post_title,
        post.published_at,
        post.published_at_readable,
        post.view_count,
        post.like_count,
        post.comment_count,
        post.share_count,
        post.bookmark_count,
        post.synced_at AS post_synced_at
    """


def detailed_row(row):
    data = row_dict(row)
    return {
        "product": {"id": data.get("product_id"), "code": data.get("product_code"), "name": data.get("product_name")},
        "country": {"id": data.get("market_id"), "code": data.get("market_code"), "name": data.get("market_name")},
        "market": {"id": data.get("market_id"), "code": data.get("market_code"), "name": data.get("market_name")},
        "account": {
            "id": data.get("account_id"),
            "reelfarm_account_id": data.get("reelfarm_account_id"),
            "username": data.get("account_username"),
            "display_name": data.get("account_display_name"),
            "avatar_url": data.get("account_avatar_url"),
            "status": data.get("account_status"),
        },
        "automation": {
            "id": data.get("automation_id"),
            "reelfarm_automation_id": data.get("reelfarm_automation_id"),
            "name": data.get("automation_name"),
            "status": data.get("automation_status"),
            "schedule": parse_json_list(data.get("automation_schedule")),
        },
        "material": {
            "id": data.get("material_id"),
            "reelfarm_video_id": data.get("reelfarm_video_id"),
            "video_type": data.get("video_type"),
            "hook": data.get("hook"),
            "prompt": data.get("prompt"),
            "slideshow_images": parse_json_list(data.get("images_json")),
            "slide_count": data.get("slide_count"),
            "status": data.get("material_status"),
            "created_at": data.get("material_created_at"),
            "finished_at": data.get("material_finished_at"),
        },
        "post": {
            "id": data.get("post_id"),
            "reelfarm_post_id": data.get("reelfarm_post_id"),
            "status": data.get("post_status"),
            "title": data.get("post_title"),
            "published_at": data.get("published_at"),
            "published_at_readable": data.get("published_at_readable"),
            "synced_at": data.get("post_synced_at"),
        },
        "metrics": {
            "view_count": data.get("view_count"),
            "like_count": data.get("like_count"),
            "comment_count": data.get("comment_count"),
            "share_count": data.get("share_count"),
            "bookmark_count": data.get("bookmark_count"),
        },
    }


def query_posts(query, top_metric=""):
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
    return [detailed_row(row) for row in rows], pagination_payload(limit, offset, rows, row_dict(total_row).get("total", 0))


def query_materials(query):
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


def query_daily_metrics(query):
    filters = query_filters(query)
    if not filters.get("date_from") and not filters.get("date_to"):
        date_from, date_to = query_days_snapshot_window(query)
        filters["date_from"] = date_from or filters.get("date_from")
        filters["date_to"] = date_to or filters.get("date_to")

    placeholder = db_placeholder()
    where_sql, params = common_where(query, date_column="snap.snapshot_date", include_post_dates=False)
    if filters.get("date_from"):
        where_sql += f" AND snap.snapshot_date >= {placeholder}"
        params.append(filters["date_from"])
    if filters.get("date_to"):
        where_sql += f" AND snap.snapshot_date <= {placeholder}"
        params.append(filters["date_to"])

    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                snap.snapshot_date,
                COUNT(DISTINCT post.id) AS post_count,
                COALESCE(SUM(snap.view_count), 0) AS views,
                COALESCE(SUM(snap.like_count), 0) AS likes,
                COALESCE(SUM(snap.comment_count), 0) AS comments,
                COALESCE(SUM(snap.share_count), 0) AS shares,
                COALESCE(SUM(snap.bookmark_count), 0) AS bookmarks
            FROM post_daily_snapshots snap
            JOIN posts post ON post.id = snap.post_id
            JOIN materials mat ON mat.id = post.material_id
            JOIN automations a ON a.id = mat.automation_id
            LEFT JOIN accounts acc ON acc.id = post.account_id
            JOIN product_market_channels pmc ON pmc.id = a.product_market_channel_id
            JOIN product_markets pm ON pm.id = pmc.product_market_id
            JOIN products p ON p.id = pm.product_id
            JOIN markets m ON m.id = pm.market_id
            JOIN channels ch ON ch.id = pmc.channel_id
            WHERE {where_sql}
            GROUP BY snap.snapshot_date
            ORDER BY snap.snapshot_date
            """,
            tuple(params),
        ).fetchall()

    data = [row_dict(row) for row in rows]
    previous = None
    for row in data:
        if previous:
            row["deltas"] = {
                "views": int(row.get("views") or 0) - int(previous.get("views") or 0),
                "likes": int(row.get("likes") or 0) - int(previous.get("likes") or 0),
                "comments": int(row.get("comments") or 0) - int(previous.get("comments") or 0),
                "shares": int(row.get("shares") or 0) - int(previous.get("shares") or 0),
                "bookmarks": int(row.get("bookmarks") or 0) - int(previous.get("bookmarks") or 0),
            }
        else:
            row["deltas"] = None
        previous = row
    return data


def data_query_payload(query):
    resource = query_value(query, "resource").lower()
    if resource not in DATA_QUERY_RESOURCES:
        raise ValueError("Unsupported or missing resource.")

    filters = compact_filters(query_filters(query))
    response = {
        "ok": True,
        "resource": resource,
        "filters": filters,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if resource == "summary":
        response["data"] = query_summary(query)
    elif resource == "product_kpis":
        response["data"] = query_product_kpis(query)
    elif resource == "product_rollups":
        response["data"] = query_product_rollups(query)
    elif resource == "country_cards":
        response["data"] = query_country_cards(query)
    elif resource == "countries":
        response["data"] = query_countries(query)
    elif resource == "accounts":
        response["data"] = query_accounts(query)
    elif resource in {"posts", "account_posts"}:
        if resource == "account_posts" and query_value(query, "source").strip().lower() in {"museon_clone", "clone", "museon"}:
            rows, pagination = query_museon_clone_account_posts(query)
        else:
            rows, pagination = query_posts(query)
        response["data"] = rows[: pagination["limit"]]
        response["pagination"] = pagination
    elif resource == "materials":
        rows, pagination = query_materials(query)
        response["data"] = rows[: pagination["limit"]]
        response["pagination"] = pagination
    elif resource == "daily_metrics":
        response["data"] = query_daily_metrics(query)
    elif resource == "top_posts":
        metric = query_value(query, "metric", "view_count")
        if metric not in DATA_QUERY_METRICS:
            raise ValueError("Unsupported metric.")
        filters["metric"] = metric
        rows, pagination = query_posts(query, top_metric=metric)
        response["filters"] = filters
        response["data"] = rows[: pagination["limit"]]
        response["pagination"] = pagination

    return response


def ai_materials_payload(query):
    product_filter = (query.get("product_code", [""])[0] or "").strip().upper()
    country_filter = (query.get("country_code", [""])[0] or "").strip().upper()
    product_id_filter = (query.get("product_id", [""])[0] or "").strip()
    country_id_filter = (query.get("country_id", [""])[0] or "").strip()
    synced_only = (query.get("synced_only", [""])[0] or "").strip().lower() in {"1", "true", "yes"}
    include_raw = (query.get("include_raw", [""])[0] or "").strip().lower() in {"1", "true", "yes"}
    placeholder = db_placeholder()
    where = []
    params = []
    if product_filter:
        where.append(f"p.code = {placeholder}")
        params.append(product_filter)
    if country_filter:
        where.append(f"m.code = {placeholder}")
        params.append(country_filter)
    if product_id_filter:
        where.append(f"p.id = {placeholder}")
        params.append(product_id_filter)
    if country_id_filter:
        where.append(f"m.id = {placeholder}")
        params.append(country_id_filter)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with connect_db() as conn:
        init_relational_schema(conn)
        pairs = conn.execute(
            f"""
            SELECT DISTINCT
                p.id AS product_id,
                p.name AS product_name,
                p.owner_type,
                p.code AS product_code,
                m.id AS market_id,
                m.name AS market_name,
                m.code AS market_code
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            {where_sql}
            ORDER BY p.name, m.code
            """,
            tuple(params),
        ).fetchall()

    countries_payload = []
    product_ids = set()
    totals = {"products": 0, "countries": 0, "creators": 0, "materials": 0, "posts": 0}
    for pair in pairs:
        result = stored_reelfarm_country(pair["product_code"], pair["market_code"])
        cards = result.get("cards", [])
        if synced_only and not cards:
            continue

        creators = []
        country_material_count = 0
        country_post_count = 0
        for card in cards:
            videos = card.get("videos") if isinstance(card.get("videos"), list) else []
            posts = card.get("posts") if isinstance(card.get("posts"), list) else []
            posts_by_video = {str(post.get("video_id")): post for post in posts if isinstance(post, dict)}
            materials = [
                {"video": video, "post": posts_by_video.get(str(video.get("video_id") or video.get("id") or ""))}
                for video in videos
                if isinstance(video, dict)
            ]
            country_material_count += len(materials)
            country_post_count += len(posts)
            creators.append(
                {
                    "account": card.get("account", {}),
                    "automation": card.get("automation", {}),
                    "material_count": len(materials),
                    "post_count": len(posts),
                    "materials": materials,
                }
            )

        product_ids.add(pair["product_id"])
        countries_payload.append(
            {
                "product": {
                    "id": pair["product_id"],
                    "name": pair["product_name"],
                    "folder": pair["owner_type"],
                    "reelFarmCode": pair["product_code"],
                },
                "country": {
                    "id": pair["market_id"],
                    "name": pair["market_name"],
                    "reelFarmCode": pair["market_code"],
                },
                "automation_prefix": f"{pair['market_code']}-{pair['product_code']}",
                "synced_at": None,
                "creator_count": len(creators),
                "material_count": country_material_count,
                "post_count": country_post_count,
                "creators": creators,
            }
        )
        totals["countries"] += 1
        totals["creators"] += len(creators)
        totals["materials"] += country_material_count
        totals["posts"] += country_post_count

    totals["products"] = len(product_ids)

    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_backend": "postgres" if using_postgres() else "sqlite",
        "filters": {
            "product_code": product_filter or None,
            "country_code": country_filter or None,
            "product_id": product_id_filter or None,
            "country_id": country_id_filter or None,
            "synced_only": synced_only,
            "include_raw": include_raw,
            "source": "relational",
        },
        "totals": totals,
        "countries": countries_payload,
    }


def find_open_port(start_port=8765):
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available local port found.")


class ManagementTableHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print("[%s] %s" % (self.log_date_time_string(), format % args))

    def send_json(self, status, payload, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return None
        raw_body = self.rfile.read(length)
        return json.loads(raw_body.decode("utf-8"))

    def cookies(self):
        cookies = {}
        raw_cookie = self.headers.get("Cookie", "")
        for part in raw_cookie.split(";"):
            if "=" not in part:
                continue
            name, value = part.strip().split("=", 1)
            cookies[name] = value
        return cookies

    def is_authenticated(self):
        return valid_auth_token(self.cookies().get(SESSION_COOKIE, ""))

    def ai_authorized(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        return external_api_key_authorized(header.removeprefix("Bearer ").strip(), "materials:read")

    def auth_required(self, path):
        if not path.startswith("/api/"):
            return False
        if path in {"/api/health", "/api/auth/login", "/api/auth/logout", "/api/auth/status"}:
            return False
        if path == "/api/reelfarm/sync-all" and cron_authorized(self.headers):
            return False
        if path == "/api/ai/materials" and self.ai_authorized():
            return False
        if path == "/api/data/query" and self.ai_authorized():
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path).path
        if self.auth_required(path) and not self.is_authenticated():
            self.send_json(401, {"error": "Unauthorized"})
            return

        if path == "/api/health":
            self.send_json(
                200,
                {
                    "ok": True,
                    "database_backend": "postgres" if using_postgres() else "sqlite",
                },
            )
            return

        if path == "/api/auth/status":
            self.send_json(200, {"authenticated": self.is_authenticated()})
            return

        if path == "/api/data":
            self.send_json(200, {"data": load_data()})
            return

        if path == "/api/database":
            self.send_json(200, database_snapshot())
            return

        if path == "/api/database/relational":
            with connect_db() as conn:
                init_relational_schema(conn)
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "database_backend": "postgres" if using_postgres() else "sqlite",
                        "tables": relational_table_counts(conn),
                    },
                )
            return

        if path == "/api/api-keys":
            self.send_json(200, {"ok": True, "keys": list_external_api_keys()})
            return

        if path == "/api/ai/materials":
            query = parse_qs(urlparse(self.path).query)
            self.send_json(200, ai_materials_payload(query))
            return

        if path == "/api/data/query":
            query = parse_qs(urlparse(self.path).query)
            try:
                self.send_json(200, data_query_payload(query))
            except ValueError as error:
                self.send_json(400, {"ok": False, "error": str(error)})
            return

        if path == "/api/growth":
            query = parse_qs(urlparse(self.path).query)
            try:
                self.send_json(200, growth_dashboard_payload(query))
            except ValueError as error:
                self.send_json(400, {"ok": False, "error": str(error)})
            return

        if path == "/api/reelfarm/config":
            self.send_json(
                200,
                {
                    "configured": bool(reelfarm_api_key()),
                    "base_url": REELFARM_BASE_URL,
                },
            )
            return

        if path == "/api/reelfarm/sync-all":
            if not cron_authorized(self.headers):
                self.send_json(401, {"error": "Unauthorized"})
                return
            try:
                self.send_json(200, sync_all_reelfarm_records())
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
            return

        if path == "/api/reelfarm/matches":
            query = parse_qs(urlparse(self.path).query)
            automation_prefix = query.get("prefix", [""])[0]
            try:
                self.send_json(200, reelfarm_matches(automation_prefix))
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
            return

        if path == "/api/reelfarm/stored-country":
            query = parse_qs(urlparse(self.path).query)
            try:
                self.send_json(
                    200,
                    stored_reelfarm_country(
                        query.get("product_code", [""])[0],
                        query.get("country_code", query.get("market_code", [""]))[0],
                    ),
                )
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
            return

        if path == "/":
            path = "/index.html"

        requested = (BASE_DIR / unquote(path.lstrip("/"))).resolve()
        if BASE_DIR not in requested.parents and requested != BASE_DIR:
            self.send_json(403, {"error": "Forbidden"})
            return

        if not requested.is_file():
            self.send_json(404, {"error": "Not found"})
            return

        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        body = requested.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/auth/login":
            try:
                payload = self.read_json_body()
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            username = str(payload.get("username", "") if isinstance(payload, dict) else "").strip()
            password = str(payload.get("password", "") if isinstance(payload, dict) else "")
            if username == ADMIN_USERNAME and hmac.compare_digest(password_hash(password), ADMIN_PASSWORD_HASH):
                token = make_auth_token(username)
                self.send_json(
                    200,
                    {"ok": True, "authenticated": True},
                    {"Set-Cookie": cookie_header(SESSION_COOKIE, token, SESSION_TTL_SECONDS)},
                )
                return

            self.send_json(401, {"error": "账号或密码不正确"})
            return

        if path == "/api/auth/logout":
            self.send_json(
                200,
                {"ok": True, "authenticated": False},
                {"Set-Cookie": cookie_header(SESSION_COOKIE, "", 0)},
            )
            return

        if self.auth_required(path) and not self.is_authenticated():
            self.send_json(401, {"error": "Unauthorized"})
            return

        if path == "/api/data":
            try:
                payload = self.read_json_body()
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                self.send_json(400, {"error": "Expected { data: [...] }"})
                return

            save_data(data)
            self.send_json(200, {"ok": True, "data": data})
            return

        if path == "/api/reset":
            data = default_data()
            save_data(data)
            self.send_json(200, {"ok": True, "data": data})
            return

        if path == "/api/reelfarm/config":
            try:
                payload = self.read_json_body()
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            api_key = str(payload.get("api_key", "") if isinstance(payload, dict) else "").strip()
            if api_key:
                save_app_value(REELFARM_API_KEY, api_key)
            else:
                delete_app_value(REELFARM_API_KEY)

            self.send_json(
                200,
                {
                    "ok": True,
                    "configured": bool(api_key),
                    "base_url": REELFARM_BASE_URL,
                },
            )
            return

        if path == "/api/api-keys":
            try:
                payload = self.read_json_body() or {}
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            name = str(payload.get("name", "") if isinstance(payload, dict) else "").strip()
            created = create_external_api_key(name, ["materials:read"])
            self.send_json(200, {"ok": True, **created})
            return

        if path == "/api/api-keys/revoke":
            try:
                payload = self.read_json_body() or {}
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            key_id = str(payload.get("id", "") if isinstance(payload, dict) else "").strip()
            try:
                self.send_json(200, {"ok": True, "record": revoke_external_api_key(key_id)})
            except ValueError as error:
                self.send_json(404, {"error": str(error)})
            return

        if path == "/api/reelfarm/sync-prefix":
            try:
                payload = self.read_json_body()
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            prefix = str(payload.get("prefix", "") if isinstance(payload, dict) else "").strip()
            try:
                self.send_json(
                    200,
                    sync_reelfarm_prefix(
                        prefix,
                        str(payload.get("product_id", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("country_id", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("concept_id", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("product_code", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("country_code", "") if isinstance(payload, dict) else "").strip(),
                    ),
                )
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
            return

        if path == "/api/reelfarm/sync-country":
            try:
                payload = self.read_json_body()
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            prefix = str(payload.get("prefix", "") if isinstance(payload, dict) else "").strip()
            try:
                self.send_json(
                    200,
                    sync_reelfarm_country(
                        prefix,
                        str(payload.get("product_id", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("country_id", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("product_code", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("country_code", "") if isinstance(payload, dict) else "").strip(),
                    ),
                )
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
            return

        if path == "/api/museon/sync-country":
            try:
                payload = self.read_json_body()
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            try:
                self.send_json(
                    200,
                    sync_museon_clone_country(
                        str(payload.get("product_id", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("country_id", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("product_code", "") if isinstance(payload, dict) else "").strip(),
                        str(payload.get("country_code", "") if isinstance(payload, dict) else "").strip(),
                    ),
                )
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
            return

        if path == "/api/growth/sync-product":
            try:
                payload = self.read_json_body() or {}
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return
            try:
                records = sync_product_growth_snapshots(
                    str(payload.get("product_code", "") if isinstance(payload, dict) else "").strip(),
                    payload.get("days", 30) if isinstance(payload, dict) else 30,
                )
                self.send_json(200, {"ok": True, "count": len(records), "records": records})
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
            return

        if path == "/api/reelfarm/sync-all":
            if not cron_authorized(self.headers):
                self.send_json(401, {"error": "Unauthorized"})
                return
            try:
                self.send_json(200, sync_all_reelfarm_records())
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
            return

        self.send_json(404, {"error": "Not found"})


if __name__ == "__main__":
    init_db()
    cloud_port = os.environ.get("PORT", "").strip()
    port = int(cloud_port) if cloud_port else find_open_port()
    host = "0.0.0.0" if cloud_port else "127.0.0.1"
    url = f"http://127.0.0.1:{port}/" if not cloud_port else f"http://{host}:{port}/"
    server = ThreadingHTTPServer((host, port), ManagementTableHandler)
    print(f"Management Table is running: {url}")
    print(f"Database backend: {'Postgres' if using_postgres() else f'SQLite ({DB_PATH})'}")
    if not cloud_port:
        webbrowser.open(url)
    server.serve_forever()
