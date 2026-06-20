import os

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from server_modules.app_runtime import SESSION_COOKIE, valid_auth_token
from server_modules.auth_utils import cron_authorized as cron_secret_authorized
from server_modules.services.api_key_runtime import authorized as external_api_key_authorized
from server_modules.settings import CRON_SECRET


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


def cron_authorized(headers) -> bool:
    return cron_secret_authorized(headers, os.environ.get("CRON_SECRET", "").strip() or CRON_SECRET)


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
