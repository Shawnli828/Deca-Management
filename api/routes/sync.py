from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import (
    MuseonSyncCountryRequest,
    ReelfarmSyncCountryRequest,
    ReelfarmSyncPrefixRequest,
)
from server_modules.services.sync_runtime import (
    sync_all_reelfarm_records,
    sync_daily_all_records,
    sync_museon_clone_country,
    sync_reelfarm_country,
    sync_reelfarm_prefix,
)

from .shared import cron_authorized, require_dashboard_auth


router = APIRouter()


@router.api_route("/api/sync/daily-all", methods=["GET", "POST"])
def sync_daily_all(request: Request, days: int = 30):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    try:
        return sync_daily_all_records(days)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/api/reelfarm/sync-prefix")
def post_reelfarm_sync_prefix(request: Request, payload: ReelfarmSyncPrefixRequest = Body(default_factory=ReelfarmSyncPrefixRequest)):
    require_dashboard_auth(request)
    try:
        return sync_reelfarm_prefix(
            payload.prefix.strip(),
            payload.product_id.strip(),
            payload.country_id.strip(),
            payload.concept_id.strip(),
            payload.product_code.strip(),
            payload.country_code.strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/api/reelfarm/sync-country")
def post_reelfarm_sync_country(request: Request, payload: ReelfarmSyncCountryRequest = Body(default_factory=ReelfarmSyncCountryRequest)):
    require_dashboard_auth(request)
    try:
        return sync_reelfarm_country(
            payload.prefix.strip(),
            payload.product_id.strip(),
            payload.country_id.strip(),
            payload.product_code.strip(),
            payload.country_code.strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/api/museon/sync-country")
def post_museon_sync_country(request: Request, payload: MuseonSyncCountryRequest = Body(default_factory=MuseonSyncCountryRequest)):
    require_dashboard_auth(request)
    try:
        return sync_museon_clone_country(
            payload.product_id.strip(),
            payload.country_id.strip(),
            payload.product_code.strip(),
            payload.country_code.strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.api_route("/api/reelfarm/sync-all", methods=["GET", "POST"])
def reelfarm_sync_all(request: Request):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    try:
        return sync_all_reelfarm_records()
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
