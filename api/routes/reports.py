from fastapi import APIRouter, HTTPException, Request

from api.schemas.responses import FeishuPreviewResponse, FlexibleResponse
from server_modules.daily_report import daily_feishu_report_text
from server_modules.services.daily_feishu_runtime import (
    ai_analysis as daily_feishu_ai_analysis,
    llm_models_payload,
    report_card as daily_feishu_report_card,
    report_card_data as daily_feishu_report_card_data,
    report_payload as daily_feishu_report_payload,
    send_report as send_daily_feishu_report,
)

from .shared import cron_authorized, require_dashboard_auth


router = APIRouter()


def truthy_query_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


@router.get("/api/reports/daily-feishu", response_model=FlexibleResponse, operation_id="get_reports_daily_feishu")
@router.post("/api/reports/daily-feishu", response_model=FlexibleResponse, operation_id="post_reports_daily_feishu")
def post_reports_daily_feishu(
    request: Request,
    date: str = "",
    include_ai: str = "",
    model: str = "",
    require_synced: str = "",
    mode: str = "text",
):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        result = send_daily_feishu_report(
            date,
            include_ai=truthy_query_value(include_ai),
            model=model,
            require_synced=truthy_query_value(require_synced),
            mode=mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to send Feishu daily report.")
    return result


@router.get(
    "/api/reports/daily-feishu-analysis",
    response_model=FlexibleResponse,
    operation_id="get_reports_daily_feishu_analysis",
)
@router.post(
    "/api/reports/daily-feishu-analysis",
    response_model=FlexibleResponse,
    operation_id="post_reports_daily_feishu_analysis",
)
def post_reports_daily_feishu_analysis(request: Request, date: str = "", model: str = ""):
    require_dashboard_auth(request)
    try:
        return daily_feishu_ai_analysis(date, model)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/reports/llm-models", response_model=FlexibleResponse)
def get_reports_llm_models(request: Request):
    require_dashboard_auth(request)
    return llm_models_payload()


@router.get("/api/reports/daily-feishu-preview", response_model=FeishuPreviewResponse)
def get_reports_daily_feishu_preview(request: Request, date: str = "", mode: str = "text"):
    require_dashboard_auth(request)
    try:
        report = daily_feishu_report_payload(date)
        message = daily_feishu_report_text(report)
        card_data = None
        card = None
        if str(mode or "").strip().lower() in {"card", "card_with_text_fallback"}:
            card_data = daily_feishu_report_card_data(report=report)
            card = daily_feishu_report_card(report=report)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "ok": True,
        "report": report,
        "message": message,
        "message_preview": message[:1200],
        "mode": mode,
        "card_data": card_data,
        "card": card,
    }
