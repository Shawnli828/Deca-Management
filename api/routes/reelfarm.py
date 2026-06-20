from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import ReelfarmConfigRequest
from api.schemas.responses import FlexibleResponse
from server_modules.services.reelfarm_runtime import (
    config_payload,
    matches,
    save_config_payload,
    stored_country,
)

from .shared import require_dashboard_auth


router = APIRouter()


@router.get("/api/reelfarm/config", response_model=FlexibleResponse)
def get_reelfarm_config(request: Request):
    require_dashboard_auth(request)
    return config_payload()


@router.post("/api/reelfarm/config", response_model=FlexibleResponse)
def post_reelfarm_config(request: Request, payload: ReelfarmConfigRequest = Body(default_factory=ReelfarmConfigRequest)):
    require_dashboard_auth(request)
    return save_config_payload(payload.api_key)


@router.get("/api/reelfarm/matches", response_model=FlexibleResponse)
def get_reelfarm_matches(request: Request, prefix: str = ""):
    require_dashboard_auth(request)
    try:
        return matches(prefix)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/reelfarm/stored-country", response_model=FlexibleResponse)
def get_reelfarm_stored_country(
    request: Request,
    product_code: str = "",
    country_code: str = "",
    market_code: str = "",
):
    require_dashboard_auth(request)
    try:
        return stored_country(product_code, country_code or market_code)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
