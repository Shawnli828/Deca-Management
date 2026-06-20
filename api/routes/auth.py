import hmac

from fastapi import APIRouter, Body, HTTPException, Request, Response

from api.schemas.requests import AuthLoginRequest
from server import (
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    cookie_header,
    make_auth_token,
    password_hash,
)

from .shared import authenticated


router = APIRouter()


@router.get("/api/auth/status")
def auth_status(request: Request):
    return {"authenticated": authenticated(request)}


@router.post("/api/auth/login")
def auth_login(response: Response, payload: AuthLoginRequest = Body(default_factory=AuthLoginRequest)):
    username = payload.username.strip()
    password = payload.password
    if username == ADMIN_USERNAME and hmac.compare_digest(password_hash(password), ADMIN_PASSWORD_HASH):
        token = make_auth_token(username)
        response.headers["Set-Cookie"] = cookie_header(SESSION_COOKIE, token, SESSION_TTL_SECONDS)
        return {"ok": True, "authenticated": True}

    raise HTTPException(status_code=401, detail="账号或密码不正确")


@router.post("/api/auth/logout")
def auth_logout(response: Response):
    response.headers["Set-Cookie"] = cookie_header(SESSION_COOKIE, "", 0)
    return {"ok": True, "authenticated": False}
