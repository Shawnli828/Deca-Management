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
    ai_materials_payload,
    cookie_header,
    create_external_api_key,
    cron_authorized,
    database_snapshot,
    default_data,
    connect_db,
    external_api_key_authorized,
    init_relational_schema,
    load_data,
    load_roaster_state,
    make_auth_token,
    password_hash,
    reelfarm_api_key,
    reelfarm_matches,
    relational_table_counts,
    rebuild_relational_data,
    revoke_external_api_key,
    save_app_value,
    save_data,
    save_roaster_state,
    sync_all_reelfarm_records,
    sync_reelfarm_country,
    sync_reelfarm_prefix,
    delete_app_value,
    REELFARM_API_KEY,
    using_postgres,
    valid_auth_token,
)
import hmac


app = FastAPI(
    title="Deca Growth API",
    description="API for Deca Growth dashboard data, ReelFarm synced materials, roaster data, and dashboard-managed API keys.",
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


def json_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


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
    return {"data": load_data()}


@app.post("/api/data")
def post_data(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    data = payload.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Expected { data: [...] }")

    save_data(data)
    return {"ok": True, "data": data}


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


@app.post("/api/database/rebuild-relational")
def post_rebuild_relational_database(
    request: Request,
    product_code: str = "",
    country_code: str = "",
    market_code: str = "",
    reset: bool = True,
):
    require_dashboard_auth(request)
    return rebuild_relational_data(
        product_code_filter=product_code,
        market_code_filter=country_code or market_code,
        reset=reset,
    )


@app.post("/api/reset")
def reset_data(request: Request):
    require_dashboard_auth(request)
    data = default_data()
    save_data(data)
    return {"ok": True, "data": data}


@app.get("/api/roaster")
def get_roaster(request: Request):
    require_dashboard_auth(request)
    return load_roaster_state()


@app.post("/api/roaster")
def post_roaster(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    require_dashboard_auth(request)
    state = payload.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=400, detail="Expected { state: {...} }")

    return {"ok": True, "state": save_roaster_state(state)}


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


@app.get("/api/reelfarm/matches")
def get_reelfarm_matches(request: Request, prefix: str = ""):
    require_dashboard_auth(request)
    try:
        return reelfarm_matches(prefix)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


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
