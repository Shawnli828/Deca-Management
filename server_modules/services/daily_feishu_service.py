from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping

from server_modules.daily_report import (
    daily_feishu_analysis_prompt,
    daily_feishu_report_text,
    default_daily_report_date,
    previous_daily_report_date,
)
from server_modules.external_clients import (
    call_daily_feishu_llm as call_daily_feishu_llm_client,
    daily_feishu_llm_api_key as daily_feishu_llm_api_key_from_env,
    daily_feishu_llm_model as daily_feishu_llm_model_from_env,
    fallback_llm_models as fallback_llm_models_from_env,
    llm_models_payload as llm_models_payload_client,
    send_feishu_message as send_feishu_message_client,
)
from server_modules.metrics_service import (
    build_daily_report_product_item,
    daily_metric_windows,
    summarize_daily_report_products,
)
from server_modules.sync_status import format_sync_readiness_line


@dataclass
class DailyFeishuReportService:
    env: Mapping[str, str]
    webhook_url: str
    webhook_secret: str
    llm_api_base: str
    llm_model: str
    fallback_llm_models: list[str]
    report_timezone_name: str
    make_ssl_context: Callable
    configured_product_codes: Callable
    configured_product_name_map: Callable
    business_material_report_payload: Callable
    daily_reelfarm_account_alerts: Callable
    product_reelfarm_country_avg_views: Callable
    sync_status_payload: Callable
    sync_readiness_payload: Callable

    def send_feishu_message(self, message):
        return send_feishu_message_client(
            message,
            self.webhook_url,
            self.webhook_secret,
            self.make_ssl_context,
        )

    def report_payload(self, report_date=""):
        report_date = str(report_date or "").strip() or default_daily_report_date()
        try:
            datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError as error:
            raise ValueError("date must use YYYY-MM-DD.") from error

        names = self.configured_product_name_map()
        products = []
        errors = []
        windows_for_day = daily_metric_windows(report_date)
        window = windows_for_day["content"]
        onboarding_window = windows_for_day["onboarding"]

        for product_code in self.configured_product_codes():
            try:
                payload = self.business_material_report_payload({
                    "product_code": [product_code],
                    "date_from": [report_date],
                    "date_to": [report_date],
                    "mode": ["published_materials"],
                })
                row = (payload.get("rows") or [{}])[0]
                account_alerts = self.daily_reelfarm_account_alerts(
                    product_code,
                    window["utc_start"],
                    window["utc_end"],
                )
                item = build_daily_report_product_item(
                    product_code,
                    names.get(product_code, product_code),
                    report_date,
                    row,
                    self.product_reelfarm_country_avg_views(
                        product_code,
                        window["utc_start"],
                        window["utc_end"],
                    ),
                    account_alerts,
                    payload.get("mixpanel") or {},
                )
                products.append(item)
            except (RuntimeError, ValueError) as error:
                errors.append({"product_code": product_code, "error": str(error)})

        totals = summarize_daily_report_products(products)
        sync_status = self.sync_status_payload()
        sync_ready = self.sync_readiness_payload(
            sync_status,
            max(window["utc_end"], onboarding_window["utc_end"]).isoformat(),
        )
        return {
            "ok": True,
            "report_date": report_date,
            "report_timezone": self.report_timezone_name,
            "business_window_local": {
                "start": window["start_local"].isoformat(),
                "end": window["end_local"].isoformat(),
            },
            "utc_window": {
                "start": window["utc_start"].isoformat(),
                "end": window["utc_end"].isoformat(),
            },
            "onboarding_window_local": {
                "start": onboarding_window["start_local"].isoformat(),
                "end": onboarding_window["end_local"].isoformat(),
            },
            "onboarding_utc_window": {
                "start": onboarding_window["utc_start"].isoformat(),
                "end": onboarding_window["utc_end"].isoformat(),
            },
            "products": products,
            "totals": totals,
            "errors": errors,
            "sync_status": sync_status,
            "sync_ready": sync_ready,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def llm_api_key(self):
        return daily_feishu_llm_api_key_from_env(self.env)

    def selected_llm_model(self, model=""):
        return daily_feishu_llm_model_from_env(model, self.env, self.llm_model)

    def selectable_llm_models(self):
        return fallback_llm_models_from_env(
            self.env,
            self.llm_model,
            self.fallback_llm_models,
        )

    def llm_models_payload(self):
        fallback_models = self.selectable_llm_models()
        return llm_models_payload_client(
            self.llm_api_key(),
            self.env.get("LLM_API_BASE", "").strip().rstrip("/") or self.llm_api_base,
            self.selected_llm_model(),
            fallback_models,
            self.llm_model,
            self.make_ssl_context,
        )

    def call_daily_feishu_llm(self, messages, model=""):
        return call_daily_feishu_llm_client(
            messages,
            self.llm_api_key(),
            self.env.get("LLM_API_BASE", "").strip().rstrip("/") or self.llm_api_base,
            self.selected_llm_model(model),
            self.make_ssl_context,
        )

    def ai_analysis(self, report_date="", model="", report=None, require_config=False):
        report = report or self.report_payload(report_date)
        previous_report = None
        try:
            previous_report = self.report_payload(previous_daily_report_date(report.get("report_date")))
        except Exception:
            previous_report = None
        messages = [
            {
                "role": "system",
                "content": "你只根据用户提供的 Deca Growth 日报数据做业务分析，避免夸张措辞，结论要可执行。",
            },
            {"role": "user", "content": daily_feishu_analysis_prompt(report, previous_report)},
        ]
        result = self.call_daily_feishu_llm(messages, model)
        if require_config and result.get("needs_api_key"):
            return {
                "ok": False,
                "error": result.get("analysis"),
                "needs_api_key": True,
                "model": result.get("model"),
            }
        result.update(
            {
                "report": report,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "message_preview": (result.get("analysis") or "")[:1200],
            }
        )
        return result

    def send_report(self, report_date="", include_ai=False, model="", require_synced=False):
        report = self.report_payload(report_date)
        if require_synced and not (report.get("sync_ready") or {}).get("ok"):
            return {
                "ok": False,
                "error": format_sync_readiness_line(report.get("sync_ready")),
                "report": report,
            }
        analysis = ""
        analysis_payload = None
        if include_ai:
            analysis_payload = self.ai_analysis(report_date, model, report=report, require_config=True)
            if not analysis_payload.get("ok"):
                return analysis_payload
            analysis = analysis_payload.get("analysis") or ""
        message = daily_feishu_report_text(report, analysis=analysis)
        sent = self.send_feishu_message(message)
        if not sent.get("ok"):
            return sent
        result = {
            "ok": True,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "report_date": report.get("report_date"),
            "totals": report.get("totals"),
            "product_count": len(report.get("products") or []),
            "error_count": len(report.get("errors") or []),
            "message_preview": message[:800],
        }
        if analysis_payload:
            result["analysis"] = analysis_payload.get("analysis")
            result["model"] = analysis_payload.get("model")
        return result
