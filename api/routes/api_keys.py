from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import ApiKeyCreateRequest, ApiKeyRevokeRequest
from server import create_external_api_key, revoke_external_api_key

from .shared import require_dashboard_auth


router = APIRouter()


@router.get("/api/api-keys")
def get_api_keys(request: Request):
    require_dashboard_auth(request)
    from server import list_external_api_keys

    return {"ok": True, "keys": list_external_api_keys()}


@router.post("/api/api-keys")
def post_api_keys(request: Request, payload: ApiKeyCreateRequest = Body(default_factory=ApiKeyCreateRequest)):
    require_dashboard_auth(request)
    name = payload.name.strip()
    created = create_external_api_key(name, ["materials:read"])
    return {"ok": True, **created}


@router.post("/api/api-keys/revoke")
def post_api_keys_revoke(request: Request, payload: ApiKeyRevokeRequest = Body(default_factory=ApiKeyRevokeRequest)):
    require_dashboard_auth(request)
    key_id = payload.id.strip()
    try:
        return {"ok": True, "record": revoke_external_api_key(key_id)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
