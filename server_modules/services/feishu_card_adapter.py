from __future__ import annotations

from datetime import datetime


COUNTRY_FLAGS = {
    "US": "🇺🇸",
    "UK": "🇬🇧",
    "GB": "🇬🇧",
    "GE": "🇩🇪",
    "DE": "🇩🇪",
    "FR": "🇫🇷",
    "IT": "🇮🇹",
    "CA": "🇨🇦",
    "BR": "🇧🇷",
    "IN": "🇮🇳",
    "CN": "🇨🇳",
    "JP": "🇯🇵",
    "KR": "🇰🇷",
    "AU": "🇦🇺",
    "AT": "🇦🇹",
    "ES": "🇪🇸",
    "NL": "🇳🇱",
}

PRODUCT_DISPLAY_ORDER = ("DeenBack", "Demi", "Delust")
ANOMALY_ACCOUNT_PREVIEW_LIMIT = 24


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def rounded_metric(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return round(number, 1)


def compact_local_datetime(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text
    return parsed.strftime("%m-%d %H:%M")


def content_window_label(report):
    window = report.get("business_window_local") or {}
    start = compact_local_datetime(window.get("start"))
    end = compact_local_datetime(window.get("end"))
    if start and end:
        return f"{start} → {end} BJT"
    return ""


def country_flag(country):
    code = str(country.get("country_code") or "").strip().upper()
    return COUNTRY_FLAGS.get(code, "🌐")


def country_label(country):
    return str(country.get("country_name") or country.get("country_code") or "Country")


def alert_account_handle(account):
    username = str(account.get("username") or account.get("display_name") or account.get("account_id") or "unknown").strip()
    return username if username.startswith("@") else f"@{username}"


def alert_account_batch(account):
    automation_names = account.get("automation_names") or []
    if not automation_names:
        return ""
    first = str(automation_names[0] or "")
    if len(automation_names) > 1:
        return f"{first} 等 {len(automation_names)} 个 automation"
    return first


def alert_account_payload(account):
    return {
        "flag": COUNTRY_FLAGS.get(str(account.get("country_code") or "").strip().upper(), "🌐"),
        "handle": alert_account_handle(account),
        "batch": alert_account_batch(account),
    }


def anomaly_group(title, accounts, hidden):
    visible_accounts = list(accounts or [])[:ANOMALY_ACCOUNT_PREVIEW_LIMIT]
    hidden_total = safe_int(hidden) + max(len(accounts or []) - len(visible_accounts), 0)
    return {
        "title": title,
        "more": f"另有 {hidden_total} 个未展示" if hidden_total else None,
        "accounts": [alert_account_payload(account) for account in visible_accounts],
    }


def anomaly_groups(alerts):
    alerts = alerts or {}
    groups = []
    missing_accounts = alerts.get("missing_accounts") or []
    missing_count = safe_int(alerts.get("missing_account_count"))
    missing_hidden = max(safe_int(alerts.get("missing_accounts_truncated")), missing_count - len(missing_accounts), 0)
    if missing_count:
        groups.append(anomaly_group(f"未发送 {missing_count}", missing_accounts, missing_hidden))

    zero_accounts = alerts.get("zero_play_accounts") or []
    zero_count = safe_int(alerts.get("zero_play_account_count"))
    zero_hidden = max(safe_int(alerts.get("zero_play_accounts_truncated")), zero_count - len(zero_accounts), 0)
    if zero_count:
        groups.append(anomaly_group(f"0播警告 {zero_count}", zero_accounts, zero_hidden))
    return groups


def country_payload(country):
    return {
        "flag": country_flag(country),
        "name": country_label(country),
        "rfAvg": rounded_metric(country.get("reelfarm_avg_views")),
        "posts": safe_int(country.get("reelfarm_posts")),
    }


def product_card_data(product):
    alerts = product.get("account_alerts") or {}
    countries = [country_payload(country) for country in product.get("countries") or []]
    countries.sort(key=lambda country: (float(country.get("rfAvg") or 0), country.get("name") or ""), reverse=True)
    return {
        "code": product.get("product_code"),
        "name": product.get("product_name") or product.get("product_code") or "Product",
        "totalPosts": safe_int(product.get("total_posts")),
        "totalPlays": safe_int(product.get("total_views")),
        "rfPlays": safe_int(product.get("reelfarm_views")),
        "clonePlays": safe_int(product.get("clone_views")),
        "rfPublished": safe_int(product.get("reelfarm_published_automations")),
        "rfExpected": safe_int(product.get("reelfarm_expected_automations")),
        "rfAvg": rounded_metric(product.get("reelfarm_avg_views")),
        "cloneAvg": rounded_metric(product.get("clone_avg_views")),
        "onboarding": safe_int(product.get("downloads")) if product.get("downloads") is not None else None,
        "downloadRate": rounded_metric(product.get("download_rate")),
        "unsent": safe_int(alerts.get("missing_account_count")),
        "zeroPlay": safe_int(alerts.get("zero_play_account_count")),
        "countries": countries,
        "anomalyGroups": anomaly_groups(alerts),
    }


def product_sort_key(product):
    name = str(product.get("name") or "")
    try:
        index = PRODUCT_DISPLAY_ORDER.index(name)
    except ValueError:
        index = len(PRODUCT_DISPLAY_ORDER)
    return (index, name)


def trend_date_label(value):
    text = str(value or "").strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%m-%d")
    except ValueError:
        return text


def trend_rows_payload(source_rows):
    output = []
    for row in source_rows or []:
        output.append({
            "date": str(row.get("date") or "")[:10],
            "label": trend_date_label(row.get("date")),
            "view": safe_int(row.get("view")),
            "download": safe_int(row.get("download")),
        })
    return output


def trend_payload(report):
    trend = report.get("trend") or []
    if isinstance(trend, dict):
        return trend_rows_payload(trend.get("overview") or [])
    return trend_rows_payload(trend)


def trend_groups_payload(report, products):
    trend = report.get("trend") or []
    if not isinstance(trend, dict):
        return [{"key": "overview", "label": "总览", "trend": trend_rows_payload(trend)}]

    product_trends = trend.get("products") or {}
    groups = [{"key": "overview", "label": "总览", "trend": trend_rows_payload(trend.get("overview") or [])}]
    for product in products or []:
        code = str(product.get("code") or "").strip().upper()
        if not code:
            continue
        groups.append({
            "key": code,
            "label": product.get("name") or code,
            "trend": trend_rows_payload(product_trends.get(code) or []),
        })
    return groups


def country_avg_trend_payload(report, products):
    trend = report.get("trend") or []
    if not isinstance(trend, dict):
        return {}

    source = trend.get("country_avg") or {}
    output = {}
    for product in products or []:
        code = str(product.get("code") or "").strip().upper()
        if not code:
            continue
        countries_by_key = {}
        for row in source.get(code) or []:
            country_code = str(row.get("country_code") or "").strip().upper()
            country_name = str(row.get("country_name") or country_code or "Country")
            key = country_code or country_name
            entry = countries_by_key.setdefault(key, {
                "countryCode": country_code,
                "countryName": country_name,
                "flag": country_flag(row),
                "rows": [],
            })
            entry["rows"].append({
                "date": str(row.get("date") or "")[:10],
                "label": trend_date_label(row.get("date")),
                "rfAvg": rounded_metric(row.get("rf_avg")),
                "posts": safe_int(row.get("posts")),
            })

        country_trends = []
        for entry in countries_by_key.values():
            entry["rows"].sort(key=lambda item: item.get("date") or "")
            latest = next(
                (
                    row
                    for row in reversed(entry.get("rows") or [])
                    if row.get("rfAvg") is not None
                ),
                {},
            )
            country_trends.append({
                **entry,
                "_sortRfAvg": float(latest.get("rfAvg") or 0),
                "_sortPosts": safe_int(latest.get("posts")),
            })

        country_trends.sort(
            key=lambda item: (
                item.get("_sortRfAvg") or 0,
                item.get("_sortPosts") or 0,
                item.get("countryName") or "",
            ),
            reverse=True,
        )
        for item in country_trends:
            item.pop("_sortRfAvg", None)
            item.pop("_sortPosts", None)
        output[code] = country_trends
    return output


def daily_report_card_data(report):
    totals = report.get("totals") or {}
    products = [product_card_data(product) for product in report.get("products") or []]
    products.sort(key=product_sort_key)
    return {
        "bizDate": report.get("report_date"),
        "window": content_window_label(report),
        "global": {
            "totalPlays": safe_int(totals.get("total_views")),
            "rfPlays": safe_int(totals.get("reelfarm_views")),
            "clonePlays": safe_int(totals.get("clone_views")),
            "rfPublished": safe_int(totals.get("reelfarm_published_automations")),
            "rfExpected": safe_int(totals.get("reelfarm_expected_automations")),
            "rfAvg": rounded_metric(totals.get("reelfarm_avg_views")),
            "cloneAvg": rounded_metric(totals.get("clone_avg_views")),
            "onboarding": safe_int(totals.get("downloads")) if totals.get("downloads") is not None else None,
            "downloadRate": rounded_metric(totals.get("download_rate")),
        },
        "products": products,
        "trend": trend_payload(report),
        "trendGroups": trend_groups_payload(report, products),
        "countryAvgTrend": country_avg_trend_payload(report, products),
    }
