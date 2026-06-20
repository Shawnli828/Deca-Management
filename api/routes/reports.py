from fastapi import APIRouter, HTTPException, Request

from server_modules.daily_report import daily_feishu_report_text
from server_modules.services.daily_feishu_runtime import (
    ai_analysis as daily_feishu_ai_analysis,
    llm_models_payload,
    report_payload as daily_feishu_report_payload,
    send_report as send_daily_feishu_report,
)

from .shared import cron_authorized, require_dashboard_auth


router = APIRouter()


def truthy_query_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


@router.api_route("/api/reports/daily-feishu", methods=["GET", "POST"])
def post_reports_daily_feishu(
    request: Request,
    date: str = "",
    include_ai: str = "",
    model: str = "",
    require_synced: str = "",
):
    if not cron_authorized(request.headers):
        require_dashboard_auth(request)
    try:
        result = send_daily_feishu_report(
            date,
            include_ai=truthy_query_value(include_ai),
            model=model,
            require_synced=truthy_query_value(require_synced),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to send Feishu daily report.")
    return result


@router.api_route("/api/reports/daily-feishu-analysis", methods=["GET", "POST"])
def post_reports_daily_feishu_analysis(request: Request, date: str = "", model: str = ""):
    require_dashboard_auth(request)
    try:
        return daily_feishu_ai_analysis(date, model)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/api/reports/llm-models")
def get_reports_llm_models(request: Request):
    require_dashboard_auth(request)
    return llm_models_payload()


@router.get("/api/reports/daily-feishu-preview")
def get_reports_daily_feishu_preview(request: Request, date: str = ""):
    require_dashboard_auth(request)
    try:
        report = daily_feishu_report_payload(date)
        message = daily_feishu_report_text(report)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "ok": True,
        "report": report,
        "message": message,
        "message_preview": message[:1200],
    }
