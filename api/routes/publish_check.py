from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import PublishCheckStateRequest
from server import (
    cron_authorized,
    load_publish_check_state,
    run_publish_check,
    save_publish_check_state,
    send_publish_check_reminder,
)

from .shared import require_dashboard_auth


router = APIRouter()


@router.get("/api/publish-check")
def get_publish_check(request: Request):
    require_dashboard_auth(request)
    return {"ok": True, "state": load_publish_check_state()}


@router.post("/api/publish-check")
def post_publish_check(request: Request, payload: PublishCheckStateRequest = Body(default_factory=PublishCheckStateRequest)):
    require_dashboard_auth(request)
    state = payload.state
    if not isinstance(state, dict):
        raise HTTPException(status_code=400, detail="Expected { state: {...} }")

    return {"ok": True, "state": save_publish_check_state(state)}


@router.api_route("/api/publish-check/run", methods=["GET", "POST"])
def post_publish_check_run(request: Request):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    return run_publish_check()


@router.post("/api/publish-check/send-reminder")
def post_publish_check_send_reminder(request: Request):
    require_dashboard_auth(request)
    result = send_publish_check_reminder()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to send Feishu reminder.")
    return result
