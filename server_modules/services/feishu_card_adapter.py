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
    return {
        "title": title,
        "more": f"另有 {hidden} 个未在源报告列出明细" if hidden else None,
        "accounts": [alert_account_payload(account) for account in accounts],
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
    }
