from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas.requests import PublishCheckStateRequest
from server_modules.services.publish_check_runtime import (
    load_state,
    run,
    save_state,
    send_reminder,
)

from .shared import cron_authorized, require_dashboard_auth


router = APIRouter()


@router.get("/api/publish-check")
def get_publish_check(request: Request):
    require_dashboard_auth(request)
    return {"ok": True, "state": load_state()}


@router.post("/api/publish-check")
def post_publish_check(request: Request, payload: PublishCheckStateRequest = Body(default_factory=PublishCheckStateRequest)):
    require_dashboard_auth(request)
    state = payload.state
    if not isinstance(state, dict):
        raise HTTPException(status_code=400, detail="Expected { state: {...} }")

    return {"ok": True, "state": save_state(state)}


@router.api_route("/api/publish-check/run", methods=["GET", "POST"])
def post_publish_check_run(request: Request):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)

    return run()


@router.post("/api/publish-check/send-reminder")
def post_publish_check_send_reminder(request: Request):
    require_dashboard_auth(request)
    result = send_reminder()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to send Feishu reminder.")
    return result
