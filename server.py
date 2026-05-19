#!/usr/bin/env python3
import json
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
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen


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
ROASTER_STATE_KEY = "roaster_state"
EXTERNAL_API_KEYS_KEY = "external_api_keys"
REELFARM_BASE_URL = "https://reel.farm/api/v1"
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
        placeholder = db_placeholder()
        row = conn.execute(
            f"SELECT key FROM app_state WHERE key = {placeholder}",
            (STATE_KEY,),
        ).fetchone()
        if row is None:
            save_data(initial_data(), conn)


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
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    save_app_value(STATE_KEY, payload, conn)


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

    return data if isinstance(data, list) else default_data()


def default_roaster_state():
    return {
        "people": [
            {"id": "han", "name": "han"},
            {"id": "li-zihan", "name": "李梓瞻"},
            {"id": "ding-lifeng", "name": "丁立峰"},
            {"id": "wang-hengjia", "name": "王恒加"},
            {"id": "jj", "name": "JJ"},
            {"id": "doris", "name": "Doris"},
            {"id": "mina", "name": "Mina"},
        ],
        "assignments": {},
    }


def normalize_roaster_state(value):
    state = value if isinstance(value, dict) else {}
    people = state.get("people") if isinstance(state.get("people"), list) else []
    assignments = state.get("assignments") if isinstance(state.get("assignments"), dict) else {}

    clean_people = []
    seen = set()
    for person in people:
        if not isinstance(person, dict):
            continue
        person_id = str(person.get("id") or "").strip()
        name = str(person.get("name") or "").strip()
        if not person_id or not name or person_id in seen:
            continue
        seen.add(person_id)
        clean_people.append({"id": person_id, "name": name})

    clean_ids = {person["id"] for person in clean_people}
    clean_assignments = {}
    for product_id, role_map in assignments.items():
        if not isinstance(role_map, dict):
            continue

        clean_role_map = {}
        for role_key, person_ids in role_map.items():
            if not isinstance(person_ids, list):
                continue

            clean_role_map[str(role_key)] = [
                str(person_id)
                for person_id in person_ids
                if str(person_id) in clean_ids
            ]

        if clean_role_map:
            clean_assignments[str(product_id)] = clean_role_map

    return {
        "people": clean_people or default_roaster_state()["people"],
        "assignments": clean_assignments,
    }


def load_roaster_state():
    value = load_app_value(ROASTER_STATE_KEY)
    if not value:
        state = default_roaster_state()
        save_app_value(ROASTER_STATE_KEY, state)
        return state

    try:
        state = json.loads(value)
    except json.JSONDecodeError:
        state = default_roaster_state()
        save_app_value(ROASTER_STATE_KEY, state)
        return state

    return normalize_roaster_state(state)


def save_roaster_state(state):
    clean_state = normalize_roaster_state(state)
    save_app_value(ROASTER_STATE_KEY, clean_state)
    return clean_state


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

    automations_payload = reelfarm_request("/automations")
    automations = list_payload(automations_payload, "automations")
    matched = [
        automation
        for automation in automations
        if str(automation.get("title", "")).lower().startswith(clean_prefix.lower())
    ]

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
        if automation_id and not automation.get("tiktok_account_id"):
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

    return {"prefix": clean_prefix, "count": len(cards), "cards": cards}


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

    for product in data:
        for country in product.get("countries", []) or []:
            prefix = build_country_automation_prefix(product, country)
            try:
                result = reelfarm_matches(prefix)
                country["reelFarmResult"] = result
                country["reelFarmSyncedAt"] = synced_at
                country["creatorCount"] = reelfarm_creator_count(result)
                country["materialCount"] = reelfarm_material_count(result)
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
            prefix_match = build_country_automation_prefix(product, country) == clean_prefix
            if not id_match and not prefix_match:
                continue

            if product_code:
                product["reelFarmCode"] = str(product_code).strip().upper()
            if country_code:
                country["reelFarmCode"] = str(country_code).strip().upper()

            result = reelfarm_matches(clean_prefix)
            country["reelFarmResult"] = result
            country["reelFarmSyncedAt"] = synced_at
            country["creatorCount"] = reelfarm_creator_count(result)
            country["materialCount"] = reelfarm_material_count(result)
            save_data(data)
            return {
                "ok": True,
                "prefix": clean_prefix,
                "synced_at": synced_at,
                "result": result,
                "creator_count": country["creatorCount"],
                "material_count": country["materialCount"],
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
                prefix_match = build_automation_prefix(product, country, concept) == clean_prefix
                if not id_match and not prefix_match:
                    continue

                if product_code:
                    product["reelFarmCode"] = str(product_code).strip().upper()
                if country_code:
                    country["reelFarmCode"] = str(country_code).strip().upper()
                result = reelfarm_matches(clean_prefix)
                concept["reelFarmResult"] = result
                concept["reelFarmSyncedAt"] = synced_at
                concept["count"] = reelfarm_creator_count(result)
                save_data(data)
                return {
                    "ok": True,
                    "prefix": clean_prefix,
                    "synced_at": synced_at,
                    "result": result,
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
        "data": data,
    }


def ai_materials_payload(query):
    data = load_data()
    product_filter = (query.get("product_code", [""])[0] or "").strip().upper()
    country_filter = (query.get("country_code", [""])[0] or "").strip().upper()
    product_id_filter = (query.get("product_id", [""])[0] or "").strip()
    country_id_filter = (query.get("country_id", [""])[0] or "").strip()
    synced_only = (query.get("synced_only", [""])[0] or "").strip().lower() in {"1", "true", "yes"}
    include_raw = (query.get("include_raw", [""])[0] or "").strip().lower() in {"1", "true", "yes"}

    countries_payload = []
    totals = {
        "products": 0,
        "countries": 0,
        "creators": 0,
        "materials": 0,
        "posts": 0,
    }

    for product in data:
        product_code = (product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
        if product_filter and product_code != product_filter:
            continue
        if product_id_filter and str(product.get("id")) != product_id_filter:
            continue

        product_included = False
        for country in product.get("countries", []) or []:
            country_code = (
                country.get("reelFarmCode")
                or COUNTRY_CODES.get(country.get("name"))
                or code_from_name(country.get("name"))
            ).upper()
            if country_filter and country_code != country_filter:
                continue
            if country_id_filter and str(country.get("id")) != country_id_filter:
                continue

            result = country.get("reelFarmResult") if isinstance(country.get("reelFarmResult"), dict) else {}
            cards = result.get("cards", []) if isinstance(result.get("cards"), list) else []
            if synced_only and not cards:
                continue

            creators = []
            country_material_count = 0
            country_post_count = 0
            for card in cards:
                if not isinstance(card, dict):
                    continue
                account = card.get("account") if isinstance(card.get("account"), dict) else {}
                automation = card.get("automation") if isinstance(card.get("automation"), dict) else {}
                videos = card.get("videos") if isinstance(card.get("videos"), list) else []
                posts = card.get("posts") if isinstance(card.get("posts"), list) else []
                posts_by_video = {str(post.get("video_id")): post for post in posts if isinstance(post, dict)}
                materials = []

                for video in videos:
                    if not isinstance(video, dict):
                        continue
                    video_id = str(video.get("video_id") or video.get("id") or "")
                    materials.append(
                        {
                            "video": video,
                            "post": posts_by_video.get(video_id),
                        }
                    )

                country_material_count += len(materials)
                country_post_count += len(posts)
                creators.append(
                    {
                        "account": account,
                        "automation": automation,
                        "material_count": len(materials),
                        "post_count": len(posts),
                        "materials": materials,
                    }
                )

            country_payload = {
                "product": {
                    "id": product.get("id"),
                    "name": product.get("name"),
                    "folder": product.get("folder"),
                    "reelFarmCode": product_code,
                },
                "country": {
                    "id": country.get("id"),
                    "name": country.get("name"),
                    "reelFarmCode": country_code,
                },
                "automation_prefix": build_country_automation_prefix(product, country),
                "synced_at": country.get("reelFarmSyncedAt"),
                "creator_count": country.get("creatorCount", reelfarm_creator_count(result)),
                "material_count": country.get("materialCount", country_material_count),
                "post_count": country_post_count,
                "creators": creators,
            }
            if include_raw:
                country_payload["raw_reelfarm_result"] = result

            countries_payload.append(country_payload)
            totals["countries"] += 1
            totals["creators"] += len(creators)
            totals["materials"] += country_material_count
            totals["posts"] += country_post_count
            product_included = True

        if product_included:
            totals["products"] += 1

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

        if path == "/api/api-keys":
            self.send_json(200, {"ok": True, "keys": list_external_api_keys()})
            return

        if path == "/api/ai/materials":
            query = parse_qs(urlparse(self.path).query)
            self.send_json(200, ai_materials_payload(query))
            return

        if path == "/api/roaster":
            self.send_json(200, load_roaster_state())
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

        if path == "/api/roaster":
            try:
                payload = self.read_json_body()
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            state = payload.get("state") if isinstance(payload, dict) else None
            if not isinstance(state, dict):
                self.send_json(400, {"error": "Expected { state: {...} }"})
                return

            self.send_json(200, {"ok": True, "state": save_roaster_state(state)})
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
