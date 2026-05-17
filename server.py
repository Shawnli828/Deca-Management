#!/usr/bin/env python3
import json
import mimetypes
import os
import re
import ssl
import sqlite3
import socket
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
REELFARM_BASE_URL = "https://reel.farm/api/v1"
SEED_DATA_PATH = BASE_DIR / "seed_data.json"
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
        "prompt_preview": prompt[:360],
    }


def compact_post(post):
    return {
        "post_id": post.get("post_id"),
        "video_id": post.get("video_id"),
        "status": post.get("status") or post.get("post_status"),
        "title": post.get("title"),
        "account_username": post.get("account_username"),
        "published_at": post.get("published_at"),
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


def sync_all_reelfarm_records():
    if not reelfarm_api_key():
        raise RuntimeError("ReelFarm API key is not configured.")

    data = load_data()
    synced_at = datetime.now(timezone.utc).isoformat()
    successes = 0
    errors = []

    for product in data:
        for country in product.get("countries", []) or []:
            for concept in country.get("concepts", []) or []:
                prefix = build_automation_prefix(product, country, concept)
                try:
                    result = reelfarm_matches(prefix)
                    concept["reelFarmResult"] = result
                    concept["reelFarmSyncedAt"] = synced_at
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


def cron_authorized(headers):
    secret = os.environ.get("CRON_SECRET", "").strip()
    if not secret:
        return True
    return headers.get("Authorization", "") == f"Bearer {secret}"


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

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return None
        raw_body = self.rfile.read(length)
        return json.loads(raw_body.decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(
                200,
                {
                    "ok": True,
                    "database_backend": "postgres" if using_postgres() else "sqlite",
                },
            )
            return

        if path == "/api/data":
            self.send_json(200, {"data": load_data()})
            return

        if path == "/api/database":
            self.send_json(200, database_snapshot())
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
