from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from server import (
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
    BASE_DIR,
    REELFARM_BASE_URL,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    account_issues_payload,
    account_tags_payload,
    add_account_issue,
    add_account_tag,
    ai_materials_payload,
    business_material_report_payload,
    cookie_header,
    create_product_tag,
    create_external_api_key,
    cron_authorized,
    database_snapshot,
    data_query_payload,
    default_data,
    delete_product_tag,
    delete_account_issue,
    delete_account_tag,
    connect_db,
    external_api_key_authorized,
    growth_dashboard_payload,
    init_relational_schema,
    load_data,
    load_publish_check_state,
    make_auth_token,
    password_hash,
    product_tags_payload,
    reelfarm_api_key,
    reelfarm_matches,
    relational_table_counts,
    revoke_external_api_key,
    save_app_value,
    save_data,
    save_publish_check_state,
    send_publish_check_reminder,
    sync_daily_all_records,
    sync_product_growth_snapshots,
    sync_all_reelfarm_records,
    sync_museon_clone_country,
    sync_reelfarm_country,
    sync_reelfarm_prefix,
    run_publish_check,
    stored_reelfarm_country,
    delete_app_value,
    enrich_data_with_relational_rollups,
    REELFARM_API_KEY,
    using_postgres,
    valid_auth_token,
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


def query_as_lists(request: Request) -> dict[str, list[str]]:
    query: dict[str, list[str]] = {}
    for key in request.query_params.keys():
        if key == "path":
            continue
        query[key] = request.query_params.getlist(key)
    return query


def authenticated(request: Request) -> bool:
    return valid_auth_token(request.cookies.get(SESSION_COOKIE, ""))


def require_dashboard_auth(request: Request) -> None:
    if not authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")


def bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return ""
    return authorization.removeprefix("Bearer ").strip()


def require_materials_api_key(authorization: str | None) -> None:
    token = bearer_token(authorization)
    if not external_api_key_authorized(token, "materials:read"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def require_data_query_auth(request: Request, authorization: str | None) -> None:
    if authenticated(request):
        return
    token = bearer_token(authorization)
    if external_api_key_authorized(token, "materials:read"):
        return
    raise HTTPException(status_code=401, detail="Unauthorized")


def json_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"ok": False, "error": message})


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


@app.get("/api/data")
def get_data(request: Request):
    require_dashboard_auth(request)
    return {"data": enrich_data_with_relational_rollups(load_data())}


@app.post("/api/data")
def post_data(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    data = payload.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Expected { data: [...] }")

    save_data(data)
    return {"ok": True, "data": enrich_data_with_relational_rollups(data)}


@app.get("/api/database")
def get_database(request: Request):
    require_dashboard_auth(request)
    return database_snapshot()


@app.get("/api/database/relational")
def get_relational_database(request: Request):
    require_dashboard_auth(request)
    with connect_db() as conn:
        init_relational_schema(conn)
        return {
            "ok": True,
            "database_backend": "postgres" if using_postgres() else "sqlite",
            "tables": relational_table_counts(conn),
        }


@app.post("/api/reset")
def reset_data(request: Request):
    require_dashboard_auth(request)
    data = default_data()
    save_data(data)
    return {"ok": True, "data": data}


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


@app.get("/api/account-tags")
def get_account_tags(request: Request, account_ids: str = ""):
    require_dashboard_auth(request)
    ids = [item.strip() for item in account_ids.split(",") if item.strip()]
    return account_tags_payload(ids)


@app.post("/api/account-tags")
def post_account_tags(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return add_account_tag(payload.get("account_id"), payload.get("tag"))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/account-tags/delete")
def post_account_tags_delete(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return delete_account_tag(payload.get("account_id"), payload.get("tag"))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/account-issues")
def get_account_issues(request: Request, account_ids: str = ""):
    require_dashboard_auth(request)
    ids = [item.strip() for item in account_ids.split(",") if item.strip()]
    return account_issues_payload(ids)


@app.post("/api/account-issues")
def post_account_issues(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return add_account_issue(payload.get("account_id"), payload.get("issue"))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/account-issues/delete")
def post_account_issues_delete(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return delete_account_issue(payload.get("account_id"), payload.get("issue"))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/product-tags")
def get_product_tags(request: Request, product_code: str = ""):
    require_dashboard_auth(request)
    try:
        return product_tags_payload(product_code)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/product-tags")
def post_product_tags(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return create_product_tag(payload.get("product_code"), payload.get("tag"))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/product-tags/delete")
def post_product_tags_delete(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        return delete_product_tag(payload.get("product_code"), payload.get("tag"), payload.get("remove_assignments", True))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


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


@app.get("/api/ai/materials")
def get_ai_materials(request: Request, authorization: str | None = Header(default=None)):
    require_materials_api_key(authorization)
    return ai_materials_payload(query_as_lists(request))


@app.get("/api/data/query")
def get_data_query(request: Request, authorization: str | None = Header(default=None)):
    require_data_query_auth(request, authorization)
    try:
        return data_query_payload(query_as_lists(request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/growth")
def get_growth_dashboard(request: Request):
    require_dashboard_auth(request)
    try:
        return growth_dashboard_payload(query_as_lists(request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/business-material-report")
def get_business_material_report(request: Request):
    require_dashboard_auth(request)
    try:
        return business_material_report_payload(query_as_lists(request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/growth/sync-product")
def post_growth_sync_product(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    try:
        records = sync_product_growth_snapshots(
            str(payload.get("product_code", "")).strip(),
            payload.get("days", 30),
        )
        return {"ok": True, "count": len(records), "records": records}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


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
