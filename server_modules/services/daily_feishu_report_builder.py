from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from server_modules.daily_report import default_daily_report_date
from server_modules.metrics_service import (
    build_daily_report_product_item,
    daily_metric_windows,
    summarize_daily_report_products,
)
from server_modules.services.daily_feishu_config import FEISHU_TREND_START_DATE


@dataclass
class DailyFeishuReportBuilder:
    report_timezone_name: str
    configured_product_codes: Callable
    configured_product_name_map: Callable
    business_material_report_payload: Callable
    daily_reelfarm_account_alerts: Callable
    product_reelfarm_country_avg_views: Callable
    sync_status_payload: Callable
    sync_readiness_payload: Callable

    def template_history(self, report, product_names=None, days=7):
        report_date = str((report or {}).get("report_date") or "").strip()
        try:
            end_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        except ValueError:
            end_date = datetime.strptime(default_daily_report_date(), "%Y-%m-%d").date()
        start_date = (end_date - timedelta(days=max(1, int(days or 7)) - 1)).isoformat()
        date_to = end_date.isoformat()
        history = {}
        for product_code in self.configured_product_codes():
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
            return {"overview": [], "products": {}, "country_avg": {}}
        dates = [
            (start_date + timedelta(days=index)).isoformat()
            for index in range((end_date - start_date).days + 1)
        ]
        if not product_codes:
            return {"overview": [], "products": {}, "country_avg": {}}

        start_date = dates[0]
        end_date_text = dates[-1]
        products = {}
        country_avg = {}
        overview_by_date = {
            date: {"date": date, "view": 0, "download": 0}
            for date in dates
        }
        content_windows_by_date = {
            date: daily_metric_windows(date)["content"]
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

            country_rows = []
            for date in dates:
                window = content_windows_by_date[date]
                try:
                    rows = self.product_reelfarm_country_avg_views(
                        code,
                        window["utc_start"],
                        window["utc_end"],
                    )
                except Exception:
                    rows = []
                for row in rows or []:
                    country_rows.append({
                        "date": date,
                        "country_code": row.get("country_code"),
                        "country_name": row.get("country_name"),
                        "rf_avg": self._safe_trend_float(row.get("reelfarm_avg_views")),
                        "posts": self._safe_trend_int(row.get("reelfarm_posts")),
                    })
            country_avg[code] = country_rows

        return {
            "overview": [overview_by_date[date] for date in dates],
            "products": products,
            "country_avg": country_avg,
        }

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

    @staticmethod
    def _safe_trend_int(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_trend_float(value):
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
