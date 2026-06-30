from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse

from api.routes.ab_tests import router as ab_tests_router
from api.routes.automation_coverage import router as automation_coverage_router
from api.routes.api_keys import router as api_keys_router
from api.routes.auth import router as auth_router
from api.routes.data import router as data_router
from api.routes.feishu_callbacks import router as feishu_callbacks_router
from api.routes.geelark import router as geelark_router
from api.routes.reelfarm import router as reelfarm_router
from api.routes.reports import router as reports_router
from api.routes.shared import json_error
from api.routes.sync import router as sync_router
from api.routes.system import router as system_router
from api.routes.tags import router as tags_router
from server_modules.app_runtime import BASE_DIR


app = FastAPI(
    title="Deca Growth API",
    description="API for Deca Growth dashboard data, ReelFarm synced materials, and dashboard-managed API keys.",
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


app.include_router(system_router)
app.include_router(auth_router)
app.include_router(data_router)
app.include_router(feishu_callbacks_router)
app.include_router(tags_router)
app.include_router(geelark_router)
app.include_router(reports_router)
app.include_router(reelfarm_router)
app.include_router(api_keys_router)
app.include_router(sync_router)
app.include_router(automation_coverage_router)
app.include_router(ab_tests_router)


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


@app.get("/{asset_path:path}")
def static_assets(asset_path: str):
    return static_file_response(asset_path)
