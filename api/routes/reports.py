from fastapi import APIRouter, HTTPException, Request

from api.schemas.responses import FeishuPreviewResponse, FlexibleResponse
from server_modules.daily_report import daily_feishu_report_text
from server_modules.services.daily_feishu_runtime import (
    report_card as daily_feishu_report_card,
    report_card_data as daily_feishu_report_card_data,
    report_payload as daily_feishu_report_payload,
    report_template_variables as daily_feishu_report_template_variables,
    send_report as send_daily_feishu_report,
)
from server_modules.services.daily_feishu_auto_send import auto_send_daily_feishu_report

from .shared import cron_authorized, require_dashboard_auth


router = APIRouter()


def truthy_query_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_feishu_mode(mode: str) -> str:
    normalized = str(mode or "template").strip().lower()
    if normalized not in {"image", "card", "card_with_text_fallback", "template"}:
        raise ValueError("mode must be image, card, card_with_text_fallback, or template.")
    return normalized


@router.get("/api/reports/daily-feishu", response_model=FlexibleResponse, operation_id="get_reports_daily_feishu")
@router.post("/api/reports/daily-feishu", response_model=FlexibleResponse, operation_id="post_reports_daily_feishu")
def post_reports_daily_feishu(
    request: Request,
    date: str = "",
    require_synced: str = "",
    mode: str = "template",
):
    is_cron_request = cron_authorized(request.headers)
    if not is_cron_request:
        require_dashboard_auth(request)
    effective_require_synced = truthy_query_value(require_synced)
    try:
        result = send_daily_feishu_report(
            date,
            require_synced=effective_require_synced,
            mode=normalize_feishu_mode(mode),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to send Feishu daily report.")
    return result


@router.get("/api/reports/daily-feishu-auto", response_model=FlexibleResponse, operation_id="get_reports_daily_feishu_auto")
@router.post("/api/reports/daily-feishu-auto", response_model=FlexibleResponse, operation_id="post_reports_daily_feishu_auto")
def post_reports_daily_feishu_auto(
    request: Request,
    date: str = "",
    delay_minutes: int = 20,
    mode: str = "template",
    force: str = "",
):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        result = auto_send_daily_feishu_report(
            date,
            delay_minutes=delay_minutes,
            mode=normalize_feishu_mode(mode),
            force=truthy_query_value(force),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to auto-send Feishu daily report.")
    return result


@router.get("/api/reports/daily-feishu-preview", response_model=FeishuPreviewResponse)
def get_reports_daily_feishu_preview(request: Request, date: str = "", mode: str = "template"):
    require_dashboard_auth(request)
    try:
        normalized_mode = normalize_feishu_mode(mode)
        report = daily_feishu_report_payload(date)
        message = daily_feishu_report_text(report)
        card_data = None
        card = None
        template_preview = None
        if normalized_mode in {"image", "card", "card_with_text_fallback", "template"}:
            card_data = daily_feishu_report_card_data(report=report)
        if normalized_mode in {"card", "card_with_text_fallback"}:
            card = daily_feishu_report_card(report=report)
        if normalized_mode == "template":
            template_preview = daily_feishu_report_template_variables(report=report)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "ok": True,
        "report": report,
        "message": message,
        "message_preview": message[:1200],
        "mode": normalized_mode,
        "card_data": card_data,
        "card": card,
        "template_preview": template_preview,
    }
