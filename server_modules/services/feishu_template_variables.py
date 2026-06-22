from __future__ import annotations

from datetime import datetime, timedelta

from server_modules.services.feishu_card_adapter import (
    COUNTRY_FLAGS,
    alert_account_batch,
    alert_account_handle,
)


DEFAULT_TEMPLATE_PRODUCT_NAMES = ("DeenBack", "Demi", "Delust")


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_text(value, precision=1):
    if value is None or value == "":
        return "—"
    number = safe_float(value)
    if number is None:
        return str(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.{precision}f}"


def compact_metric_text(value, precision=1):
    if value is None or value == "":
        return "—"
    number = safe_float(value)
    if number is None:
        return str(value)
    abs_number = abs(number)
    if abs_number >= 1_000_000:
        return f"{number / 1_000_000:.{precision}f}M"
    if abs_number >= 1_000:
        return f"{number / 1_000:.{precision}f}K"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.{precision}f}"


def percent_text(value):
    if value is None or value == "":
        return "—"
    number = safe_float(value)
    if number is None:
        return str(value)
    return f"{number:.2f}%"


def date_label(value):
    text = str(value or "").strip()
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return text
    return parsed.strftime("%m-%d")


def parse_product_names(value):
    names = [item.strip() for item in str(value or "").split(",") if item.strip()]
    return names or list(DEFAULT_TEMPLATE_PRODUCT_NAMES)


def product_name(product):
    return str(product.get("product_name") or product.get("name") or product.get("product_code") or "Product")


def product_code(product):
    return str(product.get("product_code") or product.get("code") or "").strip().upper()


def ordered_template_products(report, product_names=None):
    products = [item for item in (report or {}).get("products") or [] if isinstance(item, dict)]
    names = parse_product_names(",".join(product_names or [])) if product_names else list(DEFAULT_TEMPLATE_PRODUCT_NAMES)
    by_name = {product_name(item).strip().lower(): item for item in products}
    ordered = [by_name[name.strip().lower()] for name in names if name.strip().lower() in by_name]
    if ordered:
        return ordered
    return products[: len(names)]


def summarize_products(products):
    totals = {
        "reelfarm_views": 0,
        "clone_views": 0,
        "total_views": 0,
        "downloads": 0,
        "reelfarm_posts": 0,
        "clone_posts": 0,
        "reelfarm_published_automations": 0,
        "reelfarm_expected_automations": 0,
        "missing_account_count": 0,
        "zero_play_account_count": 0,
    }
    has_downloads = False
    for product in products or []:
        totals["reelfarm_views"] += safe_int(product.get("reelfarm_views"))
        totals["clone_views"] += safe_int(product.get("clone_views"))
        totals["total_views"] += safe_int(product.get("total_views"))
        totals["reelfarm_posts"] += safe_int(product.get("reelfarm_posts"))
        totals["clone_posts"] += safe_int(product.get("clone_posts"))
        totals["reelfarm_published_automations"] += safe_int(product.get("reelfarm_published_automations"))
        totals["reelfarm_expected_automations"] += safe_int(product.get("reelfarm_expected_automations"))
        if product.get("downloads") is not None:
            has_downloads = True
            totals["downloads"] += safe_int(product.get("downloads"))
        alerts = product.get("account_alerts") or {}
        totals["missing_account_count"] += safe_int(alerts.get("missing_account_count"))
        totals["zero_play_account_count"] += safe_int(alerts.get("zero_play_account_count"))
    totals["downloads"] = totals["downloads"] if has_downloads else None
    totals["download_rate"] = (
        totals["downloads"] / totals["total_views"] * 100
        if totals["downloads"] is not None and totals["total_views"]
        else None
    )
    totals["reelfarm_avg_views"] = (
        totals["reelfarm_views"] / totals["reelfarm_posts"]
        if totals["reelfarm_posts"]
        else None
    )
    totals["clone_avg_views"] = (
        totals["clone_views"] / totals["clone_posts"]
        if totals["clone_posts"]
        else None
    )
    return totals


def common_metric_variables(report, products):
    totals = summarize_products(products)
    missing_count = totals.get("missing_account_count")
    zero_count = totals.get("zero_play_account_count")
    return {
        "biz_date": str((report or {}).get("report_date") or ""),
        "window_label": content_window_label(report),
        "total_plays": metric_text(totals.get("total_views"), precision=0),
        "total_plays_short": compact_metric_text(totals.get("total_views")),
        "rf_plays": metric_text(totals.get("reelfarm_views"), precision=0),
        "rf_plays_short": compact_metric_text(totals.get("reelfarm_views")),
        "clone_plays": metric_text(totals.get("clone_views"), precision=0),
        "clone_plays_short": compact_metric_text(totals.get("clone_views")),
        "rf_publish_label": f"{metric_text(totals.get('reelfarm_published_automations'), precision=0)}/{metric_text(totals.get('reelfarm_expected_automations'), precision=0)}",
        "rf_avg": metric_text(totals.get("reelfarm_avg_views")),
        "clone_avg": metric_text(totals.get("clone_avg_views")),
        "onboarding": metric_text(totals.get("downloads"), precision=0),
        "download_rate": percent_text(totals.get("download_rate")),
        "unsent_accounts": metric_text(missing_count, precision=0),
        "zero_play_accounts": metric_text(zero_count, precision=0),
        "alert_summary_label": f"{metric_text(missing_count, precision=0)} / {metric_text(zero_count, precision=0)}",
    }


def content_window_label(report):
    window = (report or {}).get("business_window_local") or {}
    start = str(window.get("start") or "")
    end = str(window.get("end") or "")
    if len(start) >= 10 and len(end) >= 10:
        return f"{start[:10]} - {end[:10]}"
    return ""


def product_metric_variables(report, product):
    products = [product] if product else []
    return common_metric_variables(report, products)


def product_labels(products):
    labels = {}
    for index in range(3):
        labels[f"product_{index + 1}_label"] = product_name(products[index]) if index < len(products) else "—"
    return labels


def bar_chart(title, values, x_field, y_field, y_title):
    return {
        "type": "bar",
        "title": {"text": title},
        "data": {"values": values},
        "xField": x_field,
        "yField": y_field,
        "label": {"visible": True},
        "axes": [
            {"orient": "bottom", "label": {"autoRotate": False}},
            {"orient": "left", "title": {"visible": True, "text": y_title}},
        ],
    }


def line_chart(title, values, y_field, y_title, series_field=None):
    chart = {
        "type": "line",
        "title": {"text": title},
        "data": {"values": values},
        "xField": "date",
        "yField": y_field,
        "point": {"visible": True},
        "axes": [
            {"orient": "bottom", "label": {"autoRotate": False}},
            {"orient": "left", "title": {"visible": True, "text": y_title}},
        ],
    }
    if series_field:
        chart["seriesField"] = series_field
        chart["legends"] = {"visible": True}
    else:
        chart["legends"] = {"visible": False}
    return chart


def daily_view_download_chart(title, rows):
    values = []
    for row in rows or []:
        label = date_label(row.get("date"))
        values.append({"date": label, "metric": "View", "value": safe_int(row.get("view"))})
        values.append({"date": label, "metric": "Download", "value": safe_int(row.get("download"))})
    return line_chart(title, values, "value", "数值", "metric")


def overview_trend_rows(report):
    trend = (report or {}).get("trend") or {}
    if isinstance(trend, dict):
        return trend.get("overview") or []
    return trend or []


def product_trend_rows(report, product):
    trend = (report or {}).get("trend") or {}
    if not isinstance(trend, dict):
        return []
    return (trend.get("products") or {}).get(product_code(product)) or []


def product_daily_rows(products):
    rows = []
    for product in products or []:
        downloads = product.get("downloads")
        rows.append({
            "product": product_name(product),
            "post": f"{metric_text(product.get('reelfarm_published_automations'), precision=0)}/{metric_text(product.get('reelfarm_expected_automations'), precision=0)}",
            "view": safe_int(product.get("total_views")),
            "rf_avg": round(safe_float(product.get("reelfarm_avg_views")) or 0, 1),
            "download": safe_int(downloads) if downloads is not None else 0,
            "conversion": percent_text(product.get("download_rate")),
        })
    return rows


def country_rf_avg_trend_chart(report, product):
    trend = (report or {}).get("trend") or {}
    if not isinstance(trend, dict) or not product:
        return line_chart("国家 RF 均播趋势", [], "rf_avg", "RF 均播", "country")

    source_rows = (trend.get("country_avg") or {}).get(product_code(product)) or []
    latest_by_country = {}
    for row in source_rows:
        key = str(row.get("country_code") or row.get("country_name") or "").strip()
        if not key:
            continue
        date = str(row.get("date") or "")
        current = latest_by_country.get(key)
        if current is None or date >= str(current.get("date") or ""):
            latest_by_country[key] = row
    top_keys = {
        key
        for key, _row in sorted(
            latest_by_country.items(),
            key=lambda item: (
                safe_float(item[1].get("rf_avg")) or 0,
                safe_int(item[1].get("posts")),
                str(item[1].get("country_name") or item[0]),
            ),
            reverse=True,
        )[:6]
    }

    values = []
    for row in source_rows:
        key = str(row.get("country_code") or row.get("country_name") or "").strip()
        if key not in top_keys:
            continue
        values.append({
            "date": date_label(row.get("date")),
            "country": f"{country_flag(row.get('country_code'))} {row.get('country_name') or row.get('country_code') or 'Country'}",
            "rf_avg": round(safe_float(row.get("rf_avg")) or 0, 1),
        })
    return line_chart("国家 RF 均播趋势", values, "rf_avg", "RF 均播", "country")


def product_comparison_charts(products):
    total_values = [
        {"product": product_name(product), "total_view": safe_int(product.get("total_views"))}
        for product in products or []
    ]
    avg_values = [
        {"product": product_name(product), "avg_view": round(safe_float(product.get("reelfarm_avg_views")) or 0, 1)}
        for product in products or []
    ]
    avg_values.sort(key=lambda row: row.get("avg_view") or 0, reverse=True)
    return {
        "product_total_view_chart": bar_chart("分产品 Total View", total_values, "product", "total_view", "Total View"),
        "product_avg_view_chart": bar_chart("分产品 Avg View", avg_values, "product", "avg_view", "Avg View"),
    }


def onboarding_download_rows(products):
    return [
        {
            "product": product_name(product),
            "onboarding": safe_int(product.get("downloads")) if product.get("downloads") is not None else 0,
            "download_rate": percent_text(product.get("download_rate")),
        }
        for product in products or []
    ]


def anomaly_status_rows(products):
    rows = []
    total_unsent = 0
    total_zero = 0
    for product in products or []:
        alerts = product.get("account_alerts") or {}
        unsent = safe_int(alerts.get("missing_account_count"))
        zero_play = safe_int(alerts.get("zero_play_account_count"))
        total_unsent += unsent
        total_zero += zero_play
        rows.append({"product": product_name(product), "unsent": unsent, "zero_play": zero_play})
    rows.append({"product": "合计", "unsent": total_unsent, "zero_play": total_zero})
    return rows


def country_flag(code):
    return COUNTRY_FLAGS.get(str(code or "").strip().upper(), "🌐")


def country_rows(product):
    rows = []
    for country in (product or {}).get("countries") or []:
        rows.append({
            "country": f"{country_flag(country.get('country_code'))} {country.get('country_name') or country.get('country_code') or 'Country'}",
            "rf_avg": round(safe_float(country.get("reelfarm_avg_views")) or 0, 1),
            "posts": safe_int(country.get("reelfarm_posts")),
        })
    return sorted(rows, key=lambda row: (row.get("rf_avg") or 0, row.get("country") or ""), reverse=True)


def account_rows(accounts):
    rows = []
    for account in accounts or []:
        rows.append({
            "country": f"{country_flag(account.get('country_code'))} {account.get('country_name') or account.get('country_code') or 'Country'}",
            "tiktok_handle": alert_account_handle(account),
            "automation_name": alert_account_batch(account),
        })
    return rows


def daily_history_rows(report, product, history_by_code):
    code = product_code(product)
    rows = list((history_by_code or {}).get(code) or [])
    if rows:
        return sorted(rows, key=lambda row: str(row.get("report_date") or ""))
    return [{
        "report_date": (report or {}).get("report_date"),
        "total_views": product.get("total_views"),
        "downloads": product.get("downloads"),
    }]


def cumulative_trend_values(report, products, history_by_code, field, output_field, product_series=True):
    values = []
    for product in products or []:
        running = 0
        for row in daily_history_rows(report, product, history_by_code):
            running += safe_int(row.get(field))
            item = {
                "date": date_label(row.get("report_date")),
                output_field: running,
            }
            if product_series:
                item["product"] = product_name(product)
            else:
                item["metric"] = "累计播放" if output_field == "cumulative_views" else "累计下载"
            values.append(item)
    return values


def trend_charts(report, products, history_by_code, product_series=True):
    views_values = cumulative_trend_values(
        report,
        products,
        history_by_code,
        "total_views",
        "cumulative_views",
        product_series=product_series,
    )
    download_values = cumulative_trend_values(
        report,
        products,
        history_by_code,
        "downloads",
        "cumulative_downloads",
        product_series=product_series,
    )
    series_field = "product" if product_series else "metric"
    return {
        "cumulative_views_trend_chart": line_chart("累计播放趋势", views_values, "cumulative_views", "累计播放", series_field),
        "cumulative_downloads_trend_chart": line_chart("累计下载趋势", download_values, "cumulative_downloads", "累计下载", series_field),
    }


def overview_template_variables(report, *, product_names=None, history_by_code=None):
    products = ordered_template_products(report, product_names)
    variables = common_metric_variables(report, products)
    variables.update(product_comparison_charts(products))
    variables.update(trend_charts(report, products, history_by_code, product_series=True))
    variables["product_daily_rows"] = product_daily_rows(products)
    variables["view_download_trend_chart"] = daily_view_download_chart(
        "View / Download 日趋势",
        overview_trend_rows(report),
    )
    variables["onboarding_download_rows"] = onboarding_download_rows(products)
    variables["anomaly_status_rows"] = anomaly_status_rows(products)
    return variables


def product_for_slot(products, view_slot):
    try:
        index = int(str(view_slot or "product_1").split("_")[-1]) - 1
    except ValueError:
        index = 0
    if not products:
        return {}
    return products[max(0, min(index, len(products) - 1))]


def product_template_variables(report, *, product_names=None, history_by_code=None, view_slot="product_1"):
    products = ordered_template_products(report, product_names)
    product = product_for_slot(products, view_slot)
    alerts = product.get("account_alerts") or {}
    variables = product_labels(products)
    variables["current_product_label"] = product_name(product) if product else "—"
    variables.update(product_metric_variables(report, product))
    variables.update(trend_charts(report, [product] if product else [], history_by_code, product_series=False))
    variables["view_download_trend_chart"] = daily_view_download_chart(
        f"{product_name(product)} View / Download 日趋势" if product else "View / Download 日趋势",
        product_trend_rows(report, product),
    )
    variables["country_rf_avg_trend_chart"] = country_rf_avg_trend_chart(report, product)
    variables["country_rf_avg_rows"] = country_rows(product)
    variables["unsent_account_rows"] = account_rows(alerts.get("missing_accounts") or [])
    variables["zero_play_account_rows"] = account_rows(alerts.get("zero_play_accounts") or [])
    return variables
