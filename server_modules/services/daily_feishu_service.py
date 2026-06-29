from dataclasses import dataclass
from datetime import datetime, timezone
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
    send_image_message as send_feishu_image_message_client,
    send_template_card as send_feishu_template_card_client,
    upload_image as upload_feishu_image_client,
)
from server_modules.domain.feishu_card import build_daily_report_card
from server_modules.services.feishu_card_adapter import daily_report_card_data
from server_modules.services.feishu_svg_report import overview_png_bytes, overview_svg
from server_modules.services.feishu_template_variables import (
    overview_template_variables,
    product_template_variables,
)
from server_modules.sync_status import format_sync_readiness_line
from server_modules.services.daily_feishu_config import (
    daily_feishu_template_config,
)
from server_modules.services.daily_feishu_report_builder import DailyFeishuReportBuilder


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
        return daily_feishu_template_config(self.env)

    def report_builder(self):
        return DailyFeishuReportBuilder(
            report_timezone_name=self.report_timezone_name,
            configured_product_codes=self.configured_product_codes,
            configured_product_name_map=self.configured_product_name_map,
            business_material_report_payload=self.business_material_report_payload,
            daily_reelfarm_account_alerts=self.daily_reelfarm_account_alerts,
            product_reelfarm_country_avg_views=self.product_reelfarm_country_avg_views,
            sync_status_payload=self.sync_status_payload,
            sync_readiness_payload=self.sync_readiness_payload,
        )

    def template_history(self, report, product_names=None, days=7):
        return self.report_builder().template_history(report, product_names=product_names, days=days)

    def report_trend(self, report_date, product_codes, days=7):
        return self.report_builder().report_trend(report_date, product_codes, days=days)

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

        return {
            "ok": True,
            "overview": overview_result,
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
        return self.report_builder().report_payload(report_date)

    def report_card_data(self, report_date="", report=None):
        report = report or self.report_payload(report_date)
        return daily_report_card_data(report)

    def report_card(self, report_date="", report=None):
        card_data = self.report_card_data(report_date, report=report)
        return build_daily_report_card(card_data)

    def report_image_payload(self, report):
        card_data = self.report_card_data(report=report)
        svg = overview_svg(card_data)
        png = overview_png_bytes(card_data)
        return {
            "card_data": card_data,
            "svg": svg,
            "png": png,
        }

    def send_image_report(self, report):
        config = self.template_config()
        image_payload = self.report_image_payload(report)
        upload_result = upload_feishu_image_client(
            app_id=config.get("app_id"),
            app_secret=config.get("app_secret"),
            image_bytes=image_payload.get("png"),
            filename=f"deca-growth-{report.get('report_date') or 'daily'}.png",
            ssl_context_factory=self.make_ssl_context,
        )
        if not upload_result.get("ok"):
            return {
                "ok": False,
                "error": upload_result.get("error") or "Failed to upload Feishu report image.",
                "mode": "image",
                "report": report,
                "card_preview": image_payload.get("card_data"),
            }

        sent = send_feishu_image_message_client(
            app_id=config.get("app_id"),
            app_secret=config.get("app_secret"),
            chat_id=config.get("chat_id"),
            image_key=upload_result.get("image_key"),
            ssl_context_factory=self.make_ssl_context,
        )
        if not sent.get("ok"):
            sent["mode"] = "image"
            sent["card_preview"] = image_payload.get("card_data")
            return sent
        return {
            "ok": True,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "report_date": report.get("report_date"),
            "totals": report.get("totals"),
            "product_count": len(report.get("products") or []),
            "error_count": len(report.get("errors") or []),
            "mode": "image",
            "image_key": upload_result.get("image_key"),
            "message_id": sent.get("message_id"),
            "card_preview": image_payload.get("card_data"),
        }

    def send_report(self, report_date="", require_synced=False, mode="template"):
        mode = str(mode or "template").strip().lower()
        if mode not in {"image", "card", "card_with_text_fallback", "template"}:
            raise ValueError("mode must be image, card, card_with_text_fallback, or template.")
        report = self.report_payload(report_date)
        if require_synced and not (report.get("sync_ready") or {}).get("ok"):
            return {
                "ok": False,
                "error": format_sync_readiness_line(report.get("sync_ready")),
                "report": report,
            }

        if mode == "image":
            return self.send_image_report(report)

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
