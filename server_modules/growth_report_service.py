from datetime import datetime, timedelta, timezone


def growth_dashboard_payload(
    query,
    *,
    query_value,
    report_timezone,
    db_placeholder,
    connect_db,
    init_relational_schema,
    row_dict,
    report_timezone_name,
    mixpanel_timezone_name,
):
    product_code = query_value(query, "product_code").upper()
    if not product_code:
        raise ValueError("product_code is required.")
    try:
        days = int(query_value(query, "days", 30))
    except ValueError:
        days = 30
    days = max(1, min(180, days))
    tz = report_timezone()
    current_local = datetime.now(timezone.utc).astimezone(tz)
    today_start = datetime(current_local.year, current_local.month, current_local.day, tzinfo=tz)
    date_to = (today_start - timedelta(days=1)).date().isoformat()
    date_from = (today_start - timedelta(days=days)).date().isoformat()
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM product_daily_growth_snapshots
            WHERE product_code = {placeholder}
              AND report_date >= {placeholder}
              AND report_date <= {placeholder}
            ORDER BY report_date
            """,
            (product_code, date_from, date_to),
        ).fetchall()
    data = [row_dict(row) for row in rows]
    latest = data[-1] if data else {}
    return {
        "ok": True,
        "product_code": product_code,
        "report_timezone": report_timezone_name,
        "source_timezone": mixpanel_timezone_name,
        "date_from": date_from,
        "date_to": date_to,
        "latest": latest,
        "series": data,
        "totals": {
            "total_views": sum(int(row.get("total_views") or 0) for row in data),
            "reelfarm_views": sum(int(row.get("reelfarm_views") or 0) for row in data),
            "clone_views": sum(int(row.get("clone_views") or 0) for row in data),
            "download_count": sum(int(row.get("download_count") or 0) for row in data if row.get("download_count") is not None),
            "onboarding_unique": sum(int(row.get("onboarding_unique") or 0) for row in data if row.get("onboarding_unique") is not None),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def business_material_report_payload(
    query,
    *,
    query_value,
    business_report_windows_with_onboarding,
    product_business_material_daily_stats,
    product_business_growth_daily_stats,
    product_active_reelfarm_expected_automation_count,
    product_growth_download_daily,
    normalize_business_report_row,
    summarize_business_report_rows,
    report_timezone_name,
    mixpanel_timezone_name,
):
    product_code = query_value(query, "product_code").upper()
    if not product_code:
        raise ValueError("product_code is required.")
    mode = query_value(query, "mode", "growth_delta").strip().lower()
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    days = query_value(query, "days", 7)
    windows, onboarding_windows = business_report_windows_with_onboarding(date_from, date_to, days)
    if not windows:
        return {
            "ok": True,
            "product_code": product_code,
            "report_timezone": report_timezone_name,
            "date_from": "",
            "date_to": "",
            "rows": [],
            "totals": {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    overall_utc_start = windows[0]["utc_start"]
    overall_utc_end = windows[-1]["utc_end"]
    if mode in {"published", "published_materials", "legacy"}:
        material_daily = product_business_material_daily_stats(product_code, overall_utc_start, overall_utc_end)
        material_mode = "published_materials"
        reelfarm_expected_count = product_active_reelfarm_expected_automation_count(product_code)
    else:
        material_daily = product_business_growth_daily_stats(product_code, windows)
        material_mode = "growth_delta"
        reelfarm_expected_count = None
    download_daily = product_growth_download_daily(
        product_code,
        windows[0]["report_date"],
        windows[-1]["report_date"],
    )
    mixpanel_missing_dates = [
        window["report_date"]
        for window in windows
        if download_daily.get(window["report_date"]) is None
    ]
    rows = [
        normalize_business_report_row(
            window,
            onboarding_windows[window["report_date"]],
            material_daily.get(window["report_date"], {}),
            download_daily.get(window["report_date"]),
            material_mode,
            reelfarm_expected_count,
        )
        for window in windows
    ]
    return {
        "ok": True,
        "product_code": product_code,
        "mode": material_mode,
        "report_timezone": report_timezone_name,
        "source_timezone": mixpanel_timezone_name,
        "mixpanel": {
            "method": "cached_product_daily_growth_snapshots",
            "metric": "onboarding_unique",
            "cache_table": "product_daily_growth_snapshots",
            "cache_field": "onboarding_unique",
            "missing_dates": mixpanel_missing_dates,
        },
        "date_from": rows[0]["report_date"],
        "date_to": rows[-1]["report_date"],
        "rows": rows,
        "totals": summarize_business_report_rows(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
