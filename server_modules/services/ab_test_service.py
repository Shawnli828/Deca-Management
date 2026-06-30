from datetime import datetime, timedelta, timezone
import re

from server_modules.app_runtime import load_data, make_ssl_context
from server_modules.common import generate_id
from server_modules.domain.growth import material_daily_stats_from_rows
from server_modules.mixpanel_client import mixpanel_event_user_unique_filtered_count
from server_modules.mixpanel_utils import product_mixpanel_config, product_mixpanel_event_name
from server_modules.product_config import country_code_for, product_code_for
from server_modules.repositories import ab_test_repository
from server_modules.settings import MIXPANEL_REGION, MIXPANEL_TIMEZONE_NAME, REPORT_TIMEZONE_NAME
from server_modules.time_windows import (
    business_material_date_for_utc_datetime,
    business_material_report_windows,
    mixpanel_timezone,
    onboarding_day_window,
    parse_iso_datetime,
    report_timezone,
    source_dates_for_utc_window,
)


COUNTRY_PROPERTY_KEYS = (
    "country_code",
    "countryCode",
    "country",
    "Country",
    "$country_code",
    "$country",
    "market_code",
    "marketCode",
    "market",
    "Market",
    "geo_country",
    "geoCountry",
    "region",
)


def _clean_date(value):
    text = str(value or "").strip()[:10]
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("date must use YYYY-MM-DD.") from error
    return text


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _status_for(test):
    if str(test.get("conclusion") or "").strip():
        return "completed"
    start_date = datetime.strptime(test["start_date"], "%Y-%m-%d").date()
    end_date = start_date + timedelta(days=max(1, _safe_int(test.get("duration_days"), 7)) - 1)
    today = datetime.now(timezone.utc).astimezone(report_timezone()).date()
    if today < start_date:
        return "draft"
    if today <= end_date:
        return "running"
    return "ready"


def _periods(start_date, duration_days):
    start = datetime.strptime(_clean_date(start_date), "%Y-%m-%d").date()
    duration = max(1, min(90, _safe_int(duration_days, 7)))
    test_end = start + timedelta(days=duration - 1)
    control_end = start - timedelta(days=1)
    control_start = start - timedelta(days=duration)
    return {
        "duration_days": duration,
        "test": {"date_from": start.isoformat(), "date_to": test_end.isoformat()},
        "control": {"date_from": control_start.isoformat(), "date_to": control_end.isoformat()},
    }


def _window_range(date_from, date_to):
    windows = business_material_report_windows(date_from, date_to, days=7)
    if not windows:
        raise ValueError("No business windows resolved.")
    return windows


def _empty_stats():
    return {
        "reelfarm_posts": 0,
        "clone_posts": 0,
        "total_posts": 0,
        "reelfarm_views": 0,
        "clone_views": 0,
        "total_views": 0,
        "avg_views": None,
        "onboarding_unique": None,
        "conversion_rate": None,
        "onboarding_filter_supported": False,
        "onboarding_scope": "country",
    }


def _summarize_stats(rows, onboarding):
    total = _empty_stats()
    for row in rows:
        total["reelfarm_posts"] += _safe_int(row.get("reelfarm_posts"))
        total["clone_posts"] += _safe_int(row.get("clone_posts"))
        total["total_posts"] += _safe_int(row.get("total_posts"))
        total["reelfarm_views"] += _safe_int(row.get("reelfarm_views"))
        total["clone_views"] += _safe_int(row.get("clone_views"))
        total["total_views"] += _safe_int(row.get("total_views"))
    total["avg_views"] = total["total_views"] / total["total_posts"] if total["total_posts"] else None
    if onboarding:
        total["onboarding_filter_supported"] = bool(onboarding.get("filter_supported"))
        total["onboarding_scope"] = "country" if onboarding.get("filter_supported") else "unavailable"
        total["onboarding_unique"] = onboarding.get("count") if onboarding.get("filter_supported") else None
    if total["onboarding_unique"] is not None and total["total_views"]:
        total["conversion_rate"] = total["onboarding_unique"] / total["total_views"] * 100
    return total


def _country_matches(properties, country_code, country_name=""):
    expected = {_normalize_key(country_code), _normalize_key(country_name)}
    expected.discard("")
    supported = False
    for key in COUNTRY_PROPERTY_KEYS:
        if key not in properties:
            continue
        supported = True
        value = properties.get(key)
        values = value if isinstance(value, list) else [value]
        for item in values:
            if _normalize_key(item) in expected:
                return True, True
    return False, supported


def _product_country_names(product_code, country_code):
    product_name = product_code
    country_name = country_code
    for product in load_data():
        if not isinstance(product, dict):
            continue
        if product_code_for(product) != product_code:
            continue
        product_name = str(product.get("name") or product_code)
        for country in product.get("countries") or []:
            if isinstance(country, dict) and country_code_for(country) == country_code:
                country_name = str(country.get("name") or country_code)
                break
        break
    return product_name, country_name


def _onboarding_count(product_code, country_code, country_name, date_from, date_to):
    windows = _window_range(date_from, date_to)
    onboarding_start = onboarding_day_window(windows[0]["report_date"])["utc_start"]
    onboarding_end = onboarding_day_window(windows[-1]["report_date"])["utc_end"]
    config = product_mixpanel_config(product_code)
    event_name = product_mixpanel_event_name(product_code, "ONBOARDING")
    return mixpanel_event_user_unique_filtered_count(
        config,
        event_name,
        onboarding_start,
        onboarding_end,
        lambda properties: _country_matches(properties, country_code, country_name),
        default_region=MIXPANEL_REGION,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        make_ssl_context=make_ssl_context,
    )


def _period_stats(product_code, country_code, country_name, date_from, date_to):
    windows = _window_range(date_from, date_to)
    rows = ab_test_repository.country_business_material_rows(
        product_code,
        country_code,
        windows[0]["utc_start"],
        windows[-1]["utc_end"],
    )
    daily = material_daily_stats_from_rows(
        rows,
        parse_iso_datetime,
        business_material_date_for_utc_datetime,
    )
    normalized_rows = []
    for window in windows:
        item = daily.get(window["report_date"], {})
        reelfarm_posts = _safe_int(item.get("reelfarm_posts"))
        clone_posts = _safe_int(item.get("clone_posts"))
        total_posts = reelfarm_posts + clone_posts
        reelfarm_views = _safe_int(item.get("reelfarm_views"))
        clone_views = _safe_int(item.get("clone_views"))
        total_views = reelfarm_views + clone_views
        normalized_rows.append({
            "report_date": window["report_date"],
            "business_window_local": {
                "start": window["start_local"].isoformat(),
                "end": window["end_local"].isoformat(),
            },
            "reelfarm_posts": reelfarm_posts,
            "clone_posts": clone_posts,
            "total_posts": total_posts,
            "reelfarm_views": reelfarm_views,
            "clone_views": clone_views,
            "total_views": total_views,
            "avg_views": total_views / total_posts if total_posts else None,
        })
    onboarding = _onboarding_count(product_code, country_code, country_name, date_from, date_to)
    return {
        "date_from": windows[0]["report_date"],
        "date_to": windows[-1]["report_date"],
        "rows": normalized_rows,
        "totals": _summarize_stats(normalized_rows, onboarding),
    }


def _delta(test_value, control_value):
    if test_value is None or control_value is None:
        return {"absolute": None, "percent": None}
    absolute = test_value - control_value
    percent = (absolute / control_value * 100) if control_value else None
    return {"absolute": absolute, "percent": percent}


def _comparison(test):
    product_code = str(test.get("product_code") or "").strip().upper()
    country_code = str(test.get("country_code") or "").strip().upper()
    product_name, country_name = _product_country_names(product_code, country_code)
    periods = _periods(test.get("start_date"), test.get("duration_days"))
    control = _period_stats(product_code, country_code, country_name, **periods["control"])
    experiment = _period_stats(product_code, country_code, country_name, **periods["test"])
    return {
        "periods": periods,
        "control": control,
        "test": experiment,
        "delta": {
            "total_posts": _delta(experiment["totals"].get("total_posts"), control["totals"].get("total_posts")),
            "total_views": _delta(experiment["totals"].get("total_views"), control["totals"].get("total_views")),
            "avg_views": _delta(experiment["totals"].get("avg_views"), control["totals"].get("avg_views")),
            "onboarding_unique": _delta(experiment["totals"].get("onboarding_unique"), control["totals"].get("onboarding_unique")),
            "conversion_rate": _delta(experiment["totals"].get("conversion_rate"), control["totals"].get("conversion_rate")),
        },
        "meta": {
            "product_name": product_name,
            "country_name": country_name,
            "report_timezone": REPORT_TIMEZONE_NAME,
            "source_timezone": MIXPANEL_TIMEZONE_NAME,
        },
    }


def _normalize_test(record, include_comparison=False):
    if not record:
        return {}
    item = dict(record)
    item["duration_days"] = max(1, _safe_int(item.get("duration_days"), 7))
    item["product_code"] = str(item.get("product_code") or "").upper()
    item["country_code"] = str(item.get("country_code") or "").upper()
    item["status"] = _status_for(item)
    product_name, country_name = _product_country_names(item["product_code"], item["country_code"])
    item["product_name"] = product_name
    item["country_name"] = country_name
    item["periods"] = _periods(item["start_date"], item["duration_days"])
    if include_comparison:
        item["comparison"] = _comparison(item)
    return item


def list_tests():
    return {
        "ok": True,
        "tests": [_normalize_test(item) for item in ab_test_repository.list_ab_tests()],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_test(test_id):
    record = ab_test_repository.get_ab_test(test_id)
    if not record:
        raise ValueError("AB test not found.")
    return {
        "ok": True,
        "test": _normalize_test(record, include_comparison=True),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def create_test(payload):
    now = datetime.now(timezone.utc).isoformat()
    product_code = str(payload.get("product_code") or "").strip().upper()
    country_code = str(payload.get("country_code") or "").strip().upper()
    if not product_code or not country_code:
        raise ValueError("product_code and country_code are required.")
    start_date = _clean_date(payload.get("start_date"))
    duration_days = max(1, min(90, _safe_int(payload.get("duration_days"), 7)))
    record = {
        "id": generate_id(),
        "name": str(payload.get("name") or f"{product_code}-{country_code} AB Test").strip(),
        "product_code": product_code,
        "country_code": country_code,
        "start_date": start_date,
        "duration_days": duration_days,
        "variable": str(payload.get("variable") or "").strip(),
        "hypothesis": str(payload.get("hypothesis") or "").strip(),
        "note": str(payload.get("note") or "").strip(),
        "conclusion": str(payload.get("conclusion") or "").strip(),
        "conclusion_status": str(payload.get("conclusion_status") or "undecided").strip() or "undecided",
        "created_at": now,
        "updated_at": now,
    }
    return {"ok": True, "test": _normalize_test(ab_test_repository.create_ab_test(record), include_comparison=True)}


def update_test(test_id, payload):
    existing = ab_test_repository.get_ab_test(test_id)
    if not existing:
        raise ValueError("AB test not found.")
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    for key in (
        "name",
        "product_code",
        "country_code",
        "start_date",
        "duration_days",
        "variable",
        "hypothesis",
        "note",
        "conclusion",
        "conclusion_status",
    ):
        if key not in payload:
            continue
        value = payload.get(key)
        if key in {"product_code", "country_code"}:
            value = str(value or "").strip().upper()
        elif key == "start_date":
            value = _clean_date(value)
        elif key == "duration_days":
            value = max(1, min(90, _safe_int(value, 7)))
        else:
            value = str(value or "").strip()
        updates[key] = value
    return {"ok": True, "test": _normalize_test(ab_test_repository.update_ab_test(test_id, updates), include_comparison=True)}


def delete_test(test_id):
    existing = ab_test_repository.get_ab_test(test_id)
    if not existing:
        raise ValueError("AB test not found.")
    return {"ok": True, "deleted": ab_test_repository.delete_ab_test(test_id)}
