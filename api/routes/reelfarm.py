from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import ReelfarmConfigRequest
from server import (
    REELFARM_API_KEY,
    REELFARM_BASE_URL,
    delete_app_value,
    reelfarm_api_key,
    reelfarm_matches,
    save_app_value,
    stored_reelfarm_country,
)
from server_modules.services.reelfarm_config_service import (
    reelfarm_config_payload,
    save_reelfarm_config_payload,
)

from .shared import require_dashboard_auth


router = APIRouter()


@router.get("/api/reelfarm/config")
def get_reelfarm_config(request: Request):
    require_dashboard_auth(request)
    return reelfarm_config_payload(reelfarm_api_key=reelfarm_api_key, base_url=REELFARM_BASE_URL)


@router.post("/api/reelfarm/config")
def post_reelfarm_config(request: Request, payload: ReelfarmConfigRequest = Body(default_factory=ReelfarmConfigRequest)):
    require_dashboard_auth(request)
    return save_reelfarm_config_payload(
        payload.api_key,
        save_app_value=save_app_value,
        delete_app_value=delete_app_value,
        state_key=REELFARM_API_KEY,
        base_url=REELFARM_BASE_URL,
    )


@router.get("/api/reelfarm/matches")
def get_reelfarm_matches(request: Request, prefix: str = ""):
    require_dashboard_auth(request)
    try:
        return reelfarm_matches(prefix)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/reelfarm/stored-country")
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
