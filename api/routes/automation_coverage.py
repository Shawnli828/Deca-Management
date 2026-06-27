from typing import Literal

from fastapi import APIRouter, Body, Request
from pydantic import BaseModel, Field

from api.schemas.responses import FlexibleResponse
from server_modules.services.automation_coverage_service import (
    create_warmup_batch,
    get_automation_coverage_payload,
    save_automation_target,
    update_warmup_batch,
)

from .shared import require_dashboard_auth


router = APIRouter()


class AutomationTargetRequest(BaseModel):
    product_code: str = Field(min_length=1)
    country_code: str = Field(min_length=1)
    target_count: int = Field(ge=0)
    note: str = ""


class AutomationWarmupRequest(BaseModel):
    product_code: str = Field(min_length=1)
    country_code: str = Field(min_length=1)
    batch_name: str = ""
    account_count: int = Field(ge=1)
    warmup_start_date: str = Field(min_length=1)
    warmup_days: int = Field(default=7, ge=1, le=365)
    note: str = ""


class AutomationWarmupUpdateRequest(BaseModel):
    batch_name: str | None = None
    account_count: int | None = Field(default=None, ge=0)
    warmup_start_date: str | None = None
    warmup_days: int | None = Field(default=None, ge=1, le=365)
    status: Literal["warming", "ready", "activated", "cancelled"] | None = None
    note: str | None = None


@router.get("/api/automation-coverage", response_model=FlexibleResponse)
def get_automation_coverage(request: Request):
    require_dashboard_auth(request)
    return get_automation_coverage_payload()


@router.put("/api/automation-coverage/targets", response_model=FlexibleResponse)
def put_automation_target(request: Request, payload: AutomationTargetRequest = Body(...)):
    require_dashboard_auth(request)
    return save_automation_target(
        payload.product_code,
        payload.country_code,
        payload.target_count,
        payload.note,
    )


@router.post("/api/automation-coverage/warmups", response_model=FlexibleResponse)
def post_automation_warmup(request: Request, payload: AutomationWarmupRequest = Body(...)):
    require_dashboard_auth(request)
    return create_warmup_batch(payload.model_dump())


@router.patch("/api/automation-coverage/warmups/{batch_id}", response_model=FlexibleResponse)
def patch_automation_warmup(batch_id: str, request: Request, payload: AutomationWarmupUpdateRequest = Body(...)):
    require_dashboard_auth(request)
    return update_warmup_batch(
        batch_id,
        {key: value for key, value in payload.model_dump().items() if value is not None},
    )
