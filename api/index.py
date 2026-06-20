import json
import os
import re
import urllib.error
import urllib.request
import uuid
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse

from api.routes.data import router as data_router
from api.routes.shared import authenticated, json_error, require_dashboard_auth
from api.routes.tags import router as tags_router

from server import (
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
    BASE_DIR,
    REELFARM_BASE_URL,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    cookie_header,
    create_external_api_key,
    cron_authorized,
    daily_feishu_ai_analysis,
    daily_feishu_report_payload,
    daily_feishu_report_text,
    load_publish_check_state,
    llm_models_payload,
    make_auth_token,
    password_hash,
    reelfarm_api_key,
    reelfarm_matches,
    revoke_external_api_key,
    save_app_value,
    save_publish_check_state,
    send_daily_feishu_report,
    send_publish_check_reminder,
    sync_daily_all_records,
    sync_all_reelfarm_records,
    sync_museon_clone_country,
    sync_reelfarm_country,
    sync_reelfarm_prefix,
    run_publish_check,
    stored_reelfarm_country,
    delete_app_value,
    REELFARM_API_KEY,
    using_postgres,
)
import hmac


app = FastAPI(
    title="Deca Growth API",
    description="API for Deca Growth dashboard data, ReelFarm synced materials, publish checks, and dashboard-managed API keys.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return json_error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return json_error(400, "Invalid request.")


@app.middleware("http")
async def rewrite_vercel_route(request: Request, call_next):
    routed_path = request.query_params.get("path")
    if request.scope.get("path", "").endswith("/api/index.py") and routed_path is not None:
        clean_path = routed_path.strip("/")
        request.scope["path"] = f"/{clean_path}" if clean_path else "/"
        request.scope["raw_path"] = request.scope["path"].encode("utf-8")
    return await call_next(request)


def geelark_api_token() -> str:
    return os.environ.get("GEELARK_API_TOKEN", "").strip() or os.environ.get("GEELARK_API_KEY", "").strip()


def geelark_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = geelark_api_token()
    if not token:
        raise HTTPException(status_code=400, detail="GEELARK_API_TOKEN is not configured")

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://openapi.geelark.com{path}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "traceId": str(uuid.uuid4()),
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", "ignore")
        raise HTTPException(status_code=exc.code, detail=f"GeeLark API error: {body_text[:500]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GeeLark request failed: {exc}") from exc


def geelark_phone_items(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    container = payload.get("data")
    total = None
    items: list[dict[str, Any]] = []
    if isinstance(container, dict):
        total = container.get("total") or container.get("count")
        for key in ("items", "list", "records", "data"):
            value = container.get(key)
            if isinstance(value, list):
                items = [item for item in value if isinstance(item, dict)]
                break
    elif isinstance(container, list):
        items = [item for item in container if isinstance(item, dict)]
    return items, total if isinstance(total, int) else None


def geelark_group_name(phone: dict[str, Any]) -> str:
    group = phone.get("group") if isinstance(phone.get("group"), dict) else {}
    return str(group.get("name") or phone.get("groupName") or "")


def geelark_group_matches(group_name: str, product_code: str, country_code: str) -> bool:
    tokens = [token for token in re.split(r"[-_\\s]+", group_name.upper()) if token]
    return product_code.upper() in tokens and country_code.upper() in tokens


def sanitize_geelark_phone(phone: dict[str, Any]) -> dict[str, Any]:
    equipment = phone.get("equipmentInfo") if isinstance(phone.get("equipmentInfo"), dict) else {}
    tags = phone.get("tags") if isinstance(phone.get("tags"), list) else []
    return {
        "id": str(phone.get("id") or phone.get("phoneId") or ""),
        "serialName": phone.get("serialName") or "",
        "serialNo": phone.get("serialNo") or "",
        "groupName": geelark_group_name(phone),
        "countryName": equipment.get("countryName") or phone.get("countryName") or "",
        "timeZone": equipment.get("timeZone") or phone.get("timeZone") or "",
        "deviceModel": equipment.get("deviceModel") or "",
        "netType": equipment.get("netType") or "",
        "status": phone.get("status"),
        "rpaStatus": phone.get("rpaStatus"),
        "tags": [str(tag.get("name")) for tag in tags if isinstance(tag, dict) and tag.get("name")],
    }


def load_geelark_phones() -> tuple[list[dict[str, Any]], int | None]:
    all_phones: list[dict[str, Any]] = []
    total: int | None = None
    page_size = 100
    for page in range(1, 20):
        response = geelark_post("/open/v1/phone/list", {"page": page, "pageSize": page_size})
        if response.get("code") not in (0, "0", None):
            raise HTTPException(status_code=502, detail=response.get("msg") or response.get("message") or "GeeLark API failed")
        items, response_total = geelark_phone_items(response)
        if response_total is not None:
            total = response_total
        all_phones.extend(items)
        if len(items) < page_size:
            break
    return all_phones, total


def geelark_payload_for_pair(all_phones: list[dict[str, Any]], product_code: str, country_code: str, total: int | None = None) -> dict[str, Any]:
    clean_product = product_code.strip().upper()
    clean_country = country_code.strip().upper()
    matched = [
        sanitize_geelark_phone(phone)
        for phone in all_phones
        if geelark_group_matches(geelark_group_name(phone), clean_product, clean_country)
    ]

    groups: dict[str, dict[str, Any]] = {}
    for phone in matched:
        group_name = phone["groupName"] or f"{clean_country}-{clean_product}"
        group = groups.setdefault(
            group_name,
            {
                "id": group_name,
                "name": group_name,
                "productCode": clean_product,
                "countryCode": clean_country,
                "countryName": phone.get("countryName") or "",
                "phones": [],
            },
        )
        group["phones"].append(phone)
        if phone.get("countryName"):
            group["countryName"] = phone["countryName"]

    ordered_groups = sorted(
        groups.values(),
        key=lambda item: [int(part) if part.isdigit() else part for part in re.split(r"(\\d+)", item["name"])],
    )

    return {
        "ok": True,
        "source": "geelark",
        "filters": {"product_code": clean_product, "country_code": clean_country},
        "total_loaded": total if total is not None else len(all_phones),
        "phone_count": len(matched),
        "group_count": len(ordered_groups),
        "groups": ordered_groups,
    }


def static_file_response(asset_path: str):
    clean_path = asset_path.strip("/") or "index.html"
    requested = (BASE_DIR / clean_path).resolve()
    if BASE_DIR not in requested.parents and requested != BASE_DIR:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not requested.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(requested, headers={"Cache-Control": "no-store"})


@app.get("/")
def root_page():
    return static_file_response("index.html")


@app.get("/index.html")
def index_page():
    return static_file_response("index.html")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "framework": "fastapi",
        "database_backend": "postgres" if using_postgres() else "sqlite",
    }


@app.get("/api/auth/status")
def auth_status(request: Request):
    return {"authenticated": authenticated(request)}


@app.post("/api/auth/login")
def auth_login(response: Response, payload: dict[str, Any] = Body(default_factory=dict)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if username == ADMIN_USERNAME and hmac.compare_digest(password_hash(password), ADMIN_PASSWORD_HASH):
        token = make_auth_token(username)
        response.headers["Set-Cookie"] = cookie_header(SESSION_COOKIE, token, SESSION_TTL_SECONDS)
        return {"ok": True, "authenticated": True}

    raise HTTPException(status_code=401, detail="账号或密码不正确")


@app.post("/api/auth/logout")
def auth_logout(response: Response):
    response.headers["Set-Cookie"] = cookie_header(SESSION_COOKIE, "", 0)
    return {"ok": True, "authenticated": False}


app.include_router(data_router)
app.include_router(tags_router)


@app.get("/api/geelark/phones")
def get_geelark_phones(request: Request, product_code: str = "DB", country_code: str = "GE"):
    require_dashboard_auth(request)
    clean_product = product_code.strip().upper()
    clean_country = country_code.strip().upper()
    if not clean_product or not clean_country:
        raise HTTPException(status_code=400, detail="product_code and country_code are required")

    all_phones, total = load_geelark_phones()
    return geelark_payload_for_pair(all_phones, clean_product, clean_country, total)


@app.get("/api/geelark/phones-map")
def get_geelark_phones_map(request: Request, pairs: str = ""):
    require_dashboard_auth(request)
    parsed_pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw_pair in pairs.split(","):
        parts = [part.strip().upper() for part in raw_pair.replace("-", ":").split(":") if part.strip()]
        if len(parts) != 2:
            continue
        product_code, country_code = parts
        key = f"{product_code}:{country_code}"
        if key in seen:
            continue
        seen.add(key)
        parsed_pairs.append((product_code, country_code))

    if not parsed_pairs:
        raise HTTPException(status_code=400, detail="pairs is required, for example DB:GE,DB:US")
    if len(parsed_pairs) > 120:
        raise HTTPException(status_code=400, detail="Too many GeeLark pairs requested")

    all_phones, total = load_geelark_phones()
    items = [
        geelark_payload_for_pair(all_phones, product_code, country_code, total)
        for product_code, country_code in parsed_pairs
    ]

    return {
        "ok": True,
        "source": "geelark",
        "pairs": [item["filters"] for item in items],
        "total_loaded": total if total is not None else len(all_phones),
        "phone_count": sum(int(item.get("phone_count") or 0) for item in items),
        "group_count": sum(int(item.get("group_count") or 0) for item in items),
        "items": items,
    }


@app.get("/api/publish-check")
def get_publish_check(request: Request):
    require_dashboard_auth(request)
    return {"ok": True, "state": load_publish_check_state()}


@app.post("/api/publish-check")
def post_publish_check(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    state = payload.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=400, detail="Expected { state: {...} }")

    return {"ok": True, "state": save_publish_check_state(state)}


@app.api_route("/api/publish-check/run", methods=["GET", "POST"])
def post_publish_check_run(request: Request):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    return run_publish_check()


@app.post("/api/publish-check/send-reminder")
def post_publish_check_send_reminder(request: Request):
    require_dashboard_auth(request)
    result = send_publish_check_reminder()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to send Feishu reminder.")
    return result


def truthy_query_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


@app.api_route("/api/reports/daily-feishu", methods=["GET", "POST"])
def post_reports_daily_feishu(
    request: Request,
    date: str = "",
    include_ai: str = "",
    model: str = "",
    require_synced: str = "",
):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        result = send_daily_feishu_report(
            date,
            include_ai=truthy_query_value(include_ai),
            model=model,
            require_synced=truthy_query_value(require_synced),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to send Feishu daily report.")
    return result


@app.api_route("/api/reports/daily-feishu-analysis", methods=["GET", "POST"])
def post_reports_daily_feishu_analysis(request: Request, date: str = "", model: str = ""):
    require_dashboard_auth(request)
    try:
        return daily_feishu_ai_analysis(date, model)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/reports/llm-models")
def get_reports_llm_models(request: Request):
    require_dashboard_auth(request)
    return llm_models_payload()


@app.get("/api/reports/daily-feishu-preview")
def get_reports_daily_feishu_preview(request: Request, date: str = ""):
    require_dashboard_auth(request)
    try:
        report = daily_feishu_report_payload(date)
        message = daily_feishu_report_text(report)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "ok": True,
        "report": report,
        "message": message,
        "message_preview": message[:1200],
    }


@app.get("/api/reelfarm/config")
def get_reelfarm_config(request: Request):
    require_dashboard_auth(request)
    return {
        "configured": bool(reelfarm_api_key()),
        "base_url": REELFARM_BASE_URL,
    }


@app.post("/api/reelfarm/config")
def post_reelfarm_config(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    api_key = str(payload.get("api_key", "")).strip()
    if api_key:
        save_app_value(REELFARM_API_KEY, api_key)
    else:
        delete_app_value(REELFARM_API_KEY)

    return {
        "ok": True,
        "configured": bool(api_key),
        "base_url": REELFARM_BASE_URL,
    }


@app.get("/api/api-keys")
def get_api_keys(request: Request):
    require_dashboard_auth(request)
    from server import list_external_api_keys

    return {"ok": True, "keys": list_external_api_keys()}


@app.post("/api/api-keys")
def post_api_keys(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    name = str(payload.get("name", "")).strip()
    created = create_external_api_key(name, ["materials:read"])
    return {"ok": True, **created}


@app.post("/api/api-keys/revoke")
def post_api_keys_revoke(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    key_id = str(payload.get("id", "")).strip()
    try:
        return {"ok": True, "record": revoke_external_api_key(key_id)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.api_route("/api/sync/daily-all", methods=["GET", "POST"])
def sync_daily_all(request: Request, days: int = 30):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    try:
        return sync_daily_all_records(days)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/reelfarm/matches")
def get_reelfarm_matches(request: Request, prefix: str = ""):
    require_dashboard_auth(request)
    try:
        return reelfarm_matches(prefix)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/reelfarm/stored-country")
def get_reelfarm_stored_country(
    request: Request,
    product_code: str = "",
    country_code: str = "",
    market_code: str = "",
):
    require_dashboard_auth(request)
    try:
        return stored_reelfarm_country(product_code, country_code or market_code)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/reelfarm/sync-prefix")
def post_reelfarm_sync_prefix(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return sync_reelfarm_prefix(
            str(payload.get("prefix", "")).strip(),
            str(payload.get("product_id", "")).strip(),
            str(payload.get("country_id", "")).strip(),
            str(payload.get("concept_id", "")).strip(),
            str(payload.get("product_code", "")).strip(),
            str(payload.get("country_code", "")).strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/reelfarm/sync-country")
def post_reelfarm_sync_country(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return sync_reelfarm_country(
            str(payload.get("prefix", "")).strip(),
            str(payload.get("product_id", "")).strip(),
            str(payload.get("country_id", "")).strip(),
            str(payload.get("product_code", "")).strip(),
            str(payload.get("country_code", "")).strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/museon/sync-country")
def post_museon_sync_country(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return sync_museon_clone_country(
            str(payload.get("product_id", "")).strip(),
            str(payload.get("country_id", "")).strip(),
            str(payload.get("product_code", "")).strip(),
            str(payload.get("country_code", "")).strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.api_route("/api/reelfarm/sync-all", methods=["GET", "POST"])
def reelfarm_sync_all(request: Request):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    try:
        return sync_all_reelfarm_records()
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/{asset_path:path}")
def static_assets(asset_path: str):
    return static_file_response(asset_path)
