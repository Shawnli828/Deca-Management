from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import (
    MuseonSyncCountryRequest,
    ReelfarmSyncCountryRequest,
    ReelfarmSyncPrefixRequest,
)
from api.schemas.responses import FlexibleResponse, SyncResultResponse
from server_modules.services.sync_runtime import (
    sync_all_reelfarm_records,
    sync_daily_all_records,
    sync_museon_clone_country,
    sync_reelfarm_country,
    sync_reelfarm_prefix,
    sync_status_payload,
)

from .shared import cron_authorized, require_dashboard_auth


router = APIRouter()


@router.get("/api/sync/status", response_model=FlexibleResponse)
def get_sync_status(request: Request):
    require_dashboard_auth(request)
    return sync_status_payload()


@router.get("/api/sync/daily-all", response_model=SyncResultResponse, operation_id="get_sync_daily_all")
@router.post("/api/sync/daily-all", response_model=SyncResultResponse, operation_id="post_sync_daily_all")
def sync_daily_all(request: Request, days: int = 30):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    try:
        return sync_daily_all_records(days)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/api/reelfarm/sync-prefix", response_model=SyncResultResponse)
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


@router.post("/api/reelfarm/sync-country", response_model=SyncResultResponse)
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


@router.post("/api/museon/sync-country", response_model=SyncResultResponse)
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


@router.get("/api/reelfarm/sync-all", response_model=SyncResultResponse, operation_id="get_reelfarm_sync_all")
@router.post("/api/reelfarm/sync-all", response_model=SyncResultResponse, operation_id="post_reelfarm_sync_all")
def reelfarm_sync_all(request: Request):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    try:
        return sync_all_reelfarm_records()
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
