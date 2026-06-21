from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping

from server_modules.daily_report import (
    daily_feishu_report_text,
    default_daily_report_date,
)
from server_modules.external_clients import (
    send_feishu_card as send_feishu_card_client,
    send_feishu_message as send_feishu_message_client,
)
from server_modules.integrations.feishu_app_client import (
    feishu_template_card_response,
    send_template_card as send_feishu_template_card_client,
)
from server_modules.domain.feishu_card import build_daily_report_card
from server_modules.metrics_service import (
    build_daily_report_product_item,
    daily_metric_windows,
    summarize_daily_report_products,
)
from server_modules.services.feishu_card_adapter import daily_report_card_data
from server_modules.services.feishu_card_snapshot_service import save_daily_report_snapshot
from server_modules.services.feishu_template_variables import (
    overview_template_variables,
    parse_product_names,
    product_template_variables,
)
from server_modules.sync_status import format_sync_readiness_line


DEFAULT_FEISHU_OVERVIEW_TEMPLATE_ID = "AAqNBs4PoCeb2"
DEFAULT_FEISHU_PRODUCT_TEMPLATE_ID = "AAqNBsXlJdHqX"
DEFAULT_FEISHU_TEMPLATE_VERSION = "1.0.0"
FEISHU_TREND_START_DATE = "2026-06-20"


@dataclass
class DailyFeishuReportService:
    env: Mapping[str, str]
    webhook_url: str
    webhook_secret: str
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

    def send_feishu_card(self, card):
        return send_feishu_card_client(
            card,
            self.webhook_url,
            self.webhook_secret,
            self.make_ssl_context,
        )

    def template_config(self):
        return {
            "app_id": self.env.get("FEISHU_APP_ID", "").strip(),
            "app_secret": self.env.get("FEISHU_APP_SECRET", "").strip(),
            "chat_id": self.env.get("FEISHU_CHAT_ID", "").strip(),
            "overview_template_id": (
                self.env.get("FEISHU_OVERVIEW_TEMPLATE_ID", "").strip()
                or DEFAULT_FEISHU_OVERVIEW_TEMPLATE_ID
            ),
            "overview_template_version": (
                self.env.get("FEISHU_OVERVIEW_TEMPLATE_VERSION", "").strip()
                or DEFAULT_FEISHU_TEMPLATE_VERSION
            ),
            "product_template_id": (
                self.env.get("FEISHU_PRODUCT_TEMPLATE_ID", "").strip()
                or DEFAULT_FEISHU_PRODUCT_TEMPLATE_ID
            ),
            "product_template_version": (
                self.env.get("FEISHU_PRODUCT_TEMPLATE_VERSION", "").strip()
                or DEFAULT_FEISHU_TEMPLATE_VERSION
            ),
            "product_names": parse_product_names(self.env.get("FEISHU_TEMPLATE_PRODUCT_NAMES", "")),
        }

    def template_history(self, report, product_names=None, days=7):
        product_names = product_names or self.template_config().get("product_names")
        report_date = str((report or {}).get("report_date") or "").strip()
        try:
            end_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        except ValueError:
            end_date = datetime.strptime(default_daily_report_date(), "%Y-%m-%d").date()
        start_date = (end_date - timedelta(days=max(1, int(days or 7)) - 1)).isoformat()
        date_to = end_date.isoformat()
        names = self.configured_product_name_map()
        wanted_names = {str(name or "").strip().lower() for name in product_names or [] if str(name or "").strip()}
        history = {}
        for product_code in self.configured_product_codes():
            product_name = names.get(product_code, product_code)
            if wanted_names and str(product_name or "").strip().lower() not in wanted_names:
                continue
            try:
                payload = self.business_material_report_payload({
                    "product_code": [product_code],
                    "date_from": [start_date],
                    "date_to": [date_to],
                    "mode": ["published_materials"],
                })
            except Exception:
                continue
            history[str(product_code or "").strip().upper()] = payload.get("rows") or []
        return history

    def report_trend(self, report_date, product_codes, days=7):
        try:
            end_date = datetime.strptime(str(report_date or "")[:10], "%Y-%m-%d").date()
        except ValueError:
            end_date = datetime.strptime(default_daily_report_date(), "%Y-%m-%d").date()
        days = max(1, min(30, int(days or 7)))
        start_floor = datetime.strptime(FEISHU_TREND_START_DATE, "%Y-%m-%d").date()
        start_date = max(end_date - timedelta(days=days - 1), start_floor)
        if start_date > end_date:
            return {"overview": [], "products": {}}
        dates = [
            (start_date + timedelta(days=index)).isoformat()
            for index in range((end_date - start_date).days + 1)
        ]
        if not product_codes:
            return {"overview": [], "products": {}}

        start_date = dates[0]
        end_date_text = dates[-1]
        products = {}
        overview_by_date = {
            date: {"date": date, "view": 0, "download": 0}
            for date in dates
        }

        for product_code in product_codes:
            code = str(product_code or "").strip().upper()
            if not code:
                continue
            rows_by_date = {}
            try:
                payload = self.business_material_report_payload({
                    "product_code": [code],
                    "date_from": [start_date],
                    "date_to": [end_date_text],
                    "mode": ["published_materials"],
                })
                for row in payload.get("rows") or []:
                    row_date = str(row.get("report_date") or "")[:10]
                    if row_date:
                        rows_by_date[row_date] = {
                            "date": row_date,
                            "view": self._safe_trend_int(row.get("total_views")),
                            "download": self._safe_trend_int(row.get("downloads")),
                        }
            except Exception:
                rows_by_date = {}

            product_rows = []
            for date in dates:
                item = rows_by_date.get(date) or {"date": date, "view": 0, "download": 0}
                product_rows.append(item)
                overview_by_date[date]["view"] += item.get("view") or 0
                overview_by_date[date]["download"] += item.get("download") or 0
            products[code] = product_rows

        return {
            "overview": [overview_by_date[date] for date in dates],
            "products": products,
        }

    @staticmethod
    def _safe_trend_int(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def report_template_payload(self, report=None, report_date="", view_slot="product_1"):
        report = report or self.report_payload(report_date)
        config = self.template_config()
        history_by_code = self.template_history(report, config.get("product_names"))
        return {
            "variables": {
                "overview": overview_template_variables(
                    report,
                    product_names=config.get("product_names"),
                    history_by_code=history_by_code,
                ),
                "product": product_template_variables(
                    report,
                    product_names=config.get("product_names"),
                    history_by_code=history_by_code,
                    view_slot=view_slot,
                ),
            },
            "history_by_code": history_by_code,
            "product_names": config.get("product_names"),
        }

    def report_template_variables(self, report=None, report_date="", view_slot="product_1"):
        return self.report_template_payload(report, report_date, view_slot).get("variables")

    def send_template_cards(self, report):
        config = self.template_config()
        template_payload = self.report_template_payload(report=report)
        variables = template_payload.get("variables") or {}
        overview_result = send_feishu_template_card_client(
            app_id=config.get("app_id"),
            app_secret=config.get("app_secret"),
            chat_id=config.get("chat_id"),
            template_id=config.get("overview_template_id"),
            template_version=config.get("overview_template_version"),
            template_variables=variables.get("overview"),
            ssl_context_factory=self.make_ssl_context,
        )
        if not overview_result.get("ok"):
            return {
                "ok": False,
                "error": overview_result.get("error") or "Failed to send overview template card.",
                "overview": overview_result,
                "template_preview": variables,
            }

        product_result = send_feishu_template_card_client(
            app_id=config.get("app_id"),
            app_secret=config.get("app_secret"),
            chat_id=config.get("chat_id"),
            template_id=config.get("product_template_id"),
            template_version=config.get("product_template_version"),
            template_variables=variables.get("product"),
            ssl_context_factory=self.make_ssl_context,
        )
        if not product_result.get("ok"):
            return {
                "ok": False,
                "error": product_result.get("error") or "Failed to send product template card.",
                "overview": overview_result,
                "product": product_result,
                "template_preview": variables,
            }

        try:
            save_daily_report_snapshot(
                (product_result or {}).get("message_id"),
                report=report,
                history_by_code=template_payload.get("history_by_code"),
                product_names=template_payload.get("product_names"),
            )
        except Exception:
            pass

        return {
            "ok": True,
            "overview": overview_result,
            "product": product_result,
            "template_preview": variables,
        }

    def product_template_callback_card(
        self,
        view_slot="product_1",
        report_date="",
        report=None,
        history_by_code=None,
        product_names=None,
    ):
        report = report or self.report_payload(report_date or default_daily_report_date())
        config = self.template_config()
        if product_names is None:
            product_names = config.get("product_names")
        if history_by_code is None:
            history_by_code = self.template_history(report, product_names)
        variables = product_template_variables(
            report,
            product_names=product_names,
            history_by_code=history_by_code,
            view_slot=view_slot,
        )
        return feishu_template_card_response(
            config.get("product_template_id"),
            config.get("product_template_version"),
            variables,
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

        product_codes = self.configured_product_codes()
        for product_code in product_codes:
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
            "trend": self.report_trend(report_date, product_codes),
            "errors": errors,
            "sync_status": sync_status,
            "sync_ready": sync_ready,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def report_card_data(self, report_date="", report=None):
        report = report or self.report_payload(report_date)
        return daily_report_card_data(report)

    def report_card(self, report_date="", report=None):
        card_data = self.report_card_data(report_date, report=report)
        return build_daily_report_card(card_data)

    def send_report(self, report_date="", require_synced=False, mode="card_with_text_fallback"):
        mode = str(mode or "card_with_text_fallback").strip().lower()
        if mode not in {"card", "card_with_text_fallback", "template"}:
            raise ValueError("mode must be card, card_with_text_fallback, or template.")
        report = self.report_payload(report_date)
        if require_synced and not (report.get("sync_ready") or {}).get("ok"):
            return {
                "ok": False,
                "error": format_sync_readiness_line(report.get("sync_ready")),
                "report": report,
            }

        if mode == "template":
            sent_templates = self.send_template_cards(report)
            if not sent_templates.get("ok"):
                sent_templates["report"] = report
                return sent_templates
            return {
                "ok": True,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "report_date": report.get("report_date"),
                "totals": report.get("totals"),
                "product_count": len(report.get("products") or []),
                "error_count": len(report.get("errors") or []),
                "mode": "template",
                "template_messages": {
                    "overview_message_id": (sent_templates.get("overview") or {}).get("message_id"),
                    "product_message_id": (sent_templates.get("product") or {}).get("message_id"),
                },
                "template_preview": sent_templates.get("template_preview"),
            }

        card_data = None
        card = None
        card_error = ""
        if mode in {"card", "card_with_text_fallback"}:
            card_data = self.report_card_data(report=report)
            card = build_daily_report_card(card_data)
            sent_card = self.send_feishu_card(card)
            if sent_card.get("ok"):
                return {
                    "ok": True,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "report_date": report.get("report_date"),
                    "totals": report.get("totals"),
                    "product_count": len(report.get("products") or []),
                    "error_count": len(report.get("errors") or []),
                    "mode": "card",
                    "card_preview": card_data,
                }
            card_error = sent_card.get("error") or "Failed to send Feishu card."
            if mode == "card":
                return {
                    "ok": False,
                    "error": card_error,
                    "mode": "card",
                    "report": report,
                    "card_preview": card_data,
                }

        message = daily_feishu_report_text(report)
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
            "mode": "card_with_text_fallback",
            "fallback_reason": card_error,
            "card_preview": card_data,
        }
        return result
