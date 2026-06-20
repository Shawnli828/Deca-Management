from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import ApiKeyCreateRequest, ApiKeyRevokeRequest
from server_modules.services.api_key_runtime import create, list_keys, revoke

from .shared import require_dashboard_auth


router = APIRouter()


@router.get("/api/api-keys")
def get_api_keys(request: Request):
    require_dashboard_auth(request)
    return {"ok": True, "keys": list_keys()}


@router.post("/api/api-keys")
def post_api_keys(request: Request, payload: ApiKeyCreateRequest = Body(default_factory=ApiKeyCreateRequest)):
    require_dashboard_auth(request)
    name = payload.name.strip()
    created = create(name, ["materials:read"])
    return {"ok": True, **created}


@router.post("/api/api-keys/revoke")
def post_api_keys_revoke(request: Request, payload: ApiKeyRevokeRequest = Body(default_factory=ApiKeyRevokeRequest)):
    require_dashboard_auth(request)
    key_id = payload.id.strip()
    try:
        return {"ok": True, "record": revoke(key_id)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
