from datetime import datetime, timedelta, timezone
import json
import re

from server_modules.app_runtime import load_data, make_ssl_context
from server_modules.common import generate_id
from server_modules.domain.growth import material_daily_stats_from_rows
from server_modules.mixpanel_client import mixpanel_event_user_unique_filtered_daily_counts
from server_modules.mixpanel_utils import product_mixpanel_config, product_mixpanel_event_name
from server_modules.product_config import country_code_for, product_code_for
from server_modules.repositories import ab_test_repository
from server_modules.settings import MIXPANEL_REGION, MIXPANEL_TIMEZONE_NAME, REPORT_TIMEZONE_NAME
from server_modules.time_windows import (
    business_material_date_for_utc_datetime,
    business_material_report_windows,
    mixpanel_timezone,
    onboarding_date_for_utc_datetime,
    onboarding_day_window,
    parse_iso_datetime,
    report_timezone,
    source_dates_for_utc_window,
)


COUNTRY_PROPERTY_KEYS = (
    "mp_country_code",
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

MIXPANEL_COUNTRY_CODES_BY_NAME = {
    "australia": "AU",
    "brazil": "BR",
    "canada": "CA",
    "china": "CN",
    "france": "FR",
    "germany": "DE",
    "india": "IN",
    "italy": "IT",
    "japan": "JP",
    "southkorea": "KR",
    "unitedkingdom": "GB",
    "unitedstates": "US",
}

MIXPANEL_COUNTRY_CODES_BY_BUSINESS_CODE = {
    "GE": "DE",
    "UK": "GB",
}

WHERE_COUNTRY_CODE_KEYS = (
    "mp_country_code",
    "country_code",
    "countryCode",
    "$country_code",
    "market_code",
    "marketCode",
    "market",
    "Market",
    "geo_country",
    "geoCountry",
)

WHERE_COUNTRY_NAME_KEYS = (
    "country",
    "Country",
    "$country",
)


def _clean_date(value):
    text = str(value or "").strip()[:10]
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("date must use YYYY-MM-DD.") from error
    return text


def _date_value(value):
    return datetime.strptime(_clean_date(value), "%Y-%m-%d").date()


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _mixpanel_country_codes(country_code, country_name):
    codes = []
    business_code = str(country_code or "").strip().upper()
    if business_code:
        codes.append(business_code)
    mixpanel_code = (
        MIXPANEL_COUNTRY_CODES_BY_BUSINESS_CODE.get(business_code)
        or MIXPANEL_COUNTRY_CODES_BY_NAME.get(_normalize_key(country_name))
    )
    if mixpanel_code and mixpanel_code not in codes:
        codes.append(mixpanel_code)
    return codes


def _mixpanel_country_where_expression(country_code, country_name):
    terms = []
    for value in _mixpanel_country_codes(country_code, country_name):
        for key in WHERE_COUNTRY_CODE_KEYS:
            terms.append(f'properties[{json.dumps(key)}] == {json.dumps(value)}')
    for value in (country_name, country_code):
        clean = str(value or "").strip()
        if not clean:
            continue
        for key in WHERE_COUNTRY_NAME_KEYS:
            terms.append(f'properties[{json.dumps(key)}] == {json.dumps(clean)}')
    return " or ".join(f"({term})" for term in terms)


def _status_for(test):
    if str(test.get("conclusion") or "").strip():
        return "completed"
    periods = _periods_for_record(test)
    start_date = _date_value(periods["test"]["date_from"])
    end_date = _date_value(periods["test"]["date_to"])
    today = datetime.now(timezone.utc).astimezone(report_timezone()).date()
    if today < start_date:
        return "draft"
    if today <= end_date:
        return "running"
    return "ready"


def _inclusive_days(start, end):
    if end < start:
        raise ValueError("date range end must be on or after start.")
    days = (end - start).days + 1
    if days > 90:
        raise ValueError("date range cannot exceed 90 days.")
    return days


def _legacy_periods(start_date, duration_days):
    start = _date_value(start_date)
    duration = max(1, min(90, _safe_int(duration_days, 7)))
    test_end = start + timedelta(days=duration - 1)
    control_end = start - timedelta(days=1)
    control_start = start - timedelta(days=duration)
    return {
        "duration_days": duration,
        "test": {"date_from": start.isoformat(), "date_to": test_end.isoformat()},
        "control": {"date_from": control_start.isoformat(), "date_to": control_end.isoformat()},
    }


def _manual_periods(control_start_date, control_end_date, test_start_date, test_end_date):
    control_start = _date_value(control_start_date)
    control_end = _date_value(control_end_date)
    test_start = _date_value(test_start_date)
    test_end = _date_value(test_end_date)
    control_duration = _inclusive_days(control_start, control_end)
    test_duration = _inclusive_days(test_start, test_end)
    return {
        "mode": "manual",
        "duration_days": test_duration,
        "control_duration_days": control_duration,
        "test_duration_days": test_duration,
        "test": {"date_from": test_start.isoformat(), "date_to": test_end.isoformat()},
        "control": {"date_from": control_start.isoformat(), "date_to": control_end.isoformat()},
    }


def _periods_for_record(record):
    manual_keys = ("control_start_date", "control_end_date", "test_start_date", "test_end_date")
    manual_values = [str(record.get(key) or "").strip() for key in manual_keys]
    if all(manual_values):
        return _manual_periods(*manual_values)
    if any(manual_values):
        raise ValueError("control_start_date, control_end_date, test_start_date and test_end_date must be provided together.")
    periods = _legacy_periods(record.get("start_date"), record.get("duration_days"))
    periods["mode"] = "auto"
    periods["control_duration_days"] = periods["duration_days"]
    periods["test_duration_days"] = periods["duration_days"]
    return periods


def _period_storage_fields(record):
    periods = _periods_for_record(record)
    return {
        "start_date": periods["test"]["date_from"],
        "duration_days": periods["test_duration_days"],
        "control_start_date": periods["control"]["date_from"],
        "control_end_date": periods["control"]["date_to"],
        "test_start_date": periods["test"]["date_from"],
        "test_end_date": periods["test"]["date_to"],
    }


def _future_report_date(report_date):
    today = datetime.now(timezone.utc).astimezone(report_timezone()).date()
    return _date_value(report_date) > today


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
    expected.update(_normalize_key(code) for code in _mixpanel_country_codes(country_code, country_name))
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


def _onboarding_counts(product_code, country_code, country_name, date_from, date_to):
    windows = _window_range(date_from, date_to)
    onboarding_start = onboarding_day_window(windows[0]["report_date"])["utc_start"]
    onboarding_end = onboarding_day_window(windows[-1]["report_date"])["utc_end"]
    config = product_mixpanel_config(product_code)
    event_name = product_mixpanel_event_name(product_code, "ONBOARDING")
    return mixpanel_event_user_unique_filtered_daily_counts(
        config,
        event_name,
        onboarding_start,
        onboarding_end,
        lambda properties: _country_matches(properties, country_code, country_name),
        onboarding_date_for_utc_datetime,
        default_region=MIXPANEL_REGION,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        make_ssl_context=make_ssl_context,
        where_expression=_mixpanel_country_where_expression(country_code, country_name),
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
    onboarding = _onboarding_counts(product_code, country_code, country_name, date_from, date_to)
    onboarding_supported = bool(onboarding.get("filter_supported"))
    onboarding_daily = onboarding.get("counts") or {}
    normalized_rows = []
    for window in windows:
        if _future_report_date(window["report_date"]):
            normalized_rows.append({
                "report_date": window["report_date"],
                "business_window_local": {
                    "start": window["start_local"].isoformat(),
                    "end": window["end_local"].isoformat(),
                },
                "reelfarm_posts": None,
                "clone_posts": None,
                "total_posts": None,
                "reelfarm_views": None,
                "clone_views": None,
                "total_views": None,
                "avg_views": None,
                "onboarding_unique": None,
                "conversion_rate": None,
                "onboarding_filter_supported": onboarding_supported,
                "onboarding_scope": "country" if onboarding_supported else "unavailable",
                "is_future": True,
            })
            continue
        item = daily.get(window["report_date"], {})
        reelfarm_posts = _safe_int(item.get("reelfarm_posts"))
        clone_posts = _safe_int(item.get("clone_posts"))
        total_posts = reelfarm_posts + clone_posts
        reelfarm_views = _safe_int(item.get("reelfarm_views"))
        clone_views = _safe_int(item.get("clone_views"))
        total_views = reelfarm_views + clone_views
        onboarding_unique = _safe_int(onboarding_daily.get(window["report_date"])) if onboarding_supported else None
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
            "onboarding_unique": onboarding_unique,
            "conversion_rate": onboarding_unique / total_views * 100 if onboarding_unique is not None and total_views else None,
            "onboarding_filter_supported": onboarding_supported,
            "onboarding_scope": "country" if onboarding_supported else "unavailable",
            "is_future": False,
        })
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
    periods = _periods_for_record(test)
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
    item["product_code"] = str(item.get("product_code") or "").upper()
    item["country_code"] = str(item.get("country_code") or "").upper()
    periods = _periods_for_record(item)
    item.update(_period_storage_fields(item))
    item["duration_days"] = periods["test_duration_days"]
    item["status"] = _status_for(item)
    product_name, country_name = _product_country_names(item["product_code"], item["country_code"])
    item["product_name"] = product_name
    item["country_name"] = country_name
    item["periods"] = periods
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
    period_fields = _period_storage_fields(payload)
    record = {
        "id": generate_id(),
        "name": str(payload.get("name") or f"{product_code}-{country_code} AB Test").strip(),
        "product_code": product_code,
        "country_code": country_code,
        **period_fields,
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
    period_keys = {
        "start_date",
        "duration_days",
        "control_start_date",
        "control_end_date",
        "test_start_date",
        "test_end_date",
    }
    for key in (
        "name",
        "product_code",
        "country_code",
        "start_date",
        "duration_days",
        "control_start_date",
        "control_end_date",
        "test_start_date",
        "test_end_date",
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
        elif key in {"start_date", "control_start_date", "control_end_date", "test_start_date", "test_end_date"}:
            value = _clean_date(value)
        elif key == "duration_days":
            value = max(1, min(90, _safe_int(value, 7)))
        else:
            value = str(value or "").strip()
        updates[key] = value
    if period_keys.intersection(updates):
        merged = {**existing, **updates}
        updates.update(_period_storage_fields(merged))
    return {"ok": True, "test": _normalize_test(ab_test_repository.update_ab_test(test_id, updates), include_comparison=True)}


def delete_test(test_id):
    existing = ab_test_repository.get_ab_test(test_id)
    if not existing:
        raise ValueError("AB test not found.")
    return {"ok": True, "deleted": ab_test_repository.delete_ab_test(test_id)}
