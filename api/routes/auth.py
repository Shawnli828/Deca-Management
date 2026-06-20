import hmac

from fastapi import APIRouter, Body, HTTPException, Request, Response

from api.schemas.requests import AuthLoginRequest
from api.schemas.responses import AuthStatusResponse, OkResponse
from server_modules.app_runtime import (
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    make_auth_token,
)
from server_modules.auth_utils import (
    cookie_header,
    password_hash,
)

from .shared import authenticated


router = APIRouter()


@router.get("/api/auth/status", response_model=AuthStatusResponse)
def auth_status(request: Request):
    return {"authenticated": authenticated(request)}


@router.post("/api/auth/login", response_model=OkResponse)
def auth_login(response: Response, payload: AuthLoginRequest = Body(default_factory=AuthLoginRequest)):
    username = payload.username.strip()
    password = payload.password
    if username == ADMIN_USERNAME and hmac.compare_digest(password_hash(password), ADMIN_PASSWORD_HASH):
        token = make_auth_token(username)
        response.headers["Set-Cookie"] = cookie_header(SESSION_COOKIE, token, SESSION_TTL_SECONDS)
        return {"ok": True, "authenticated": True}

    raise HTTPException(status_code=401, detail="账号或密码不正确")


@router.post("/api/auth/logout", response_model=OkResponse)
def auth_logout(response: Response):
    response.headers["Set-Cookie"] = cookie_header(SESSION_COOKIE, "", 0)
    return {"ok": True, "authenticated": False}
