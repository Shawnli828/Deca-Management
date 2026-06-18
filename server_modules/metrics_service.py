from server_modules.time_windows import (
    business_material_report_windows,
    mixpanel_timezone,
    onboarding_day_window,
    parse_iso_datetime,
    source_dates_for_utc_window,
    business_material_day_window,
)


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def business_report_windows_with_onboarding(date_from="", date_to="", days=7):
    windows = business_material_report_windows(date_from, date_to, days)
    onboarding_windows = {
        window["report_date"]: onboarding_day_window(window["report_date"])
        for window in windows
    }
    return windows, onboarding_windows


def daily_metric_windows(report_date=""):
    return {
        "content": business_material_day_window(report_date),
        "onboarding": onboarding_day_window(report_date),
    }


def normalize_business_report_row(
    window,
    onboarding_window,
    stats,
    downloads,
    material_mode,
    reelfarm_expected_count=None,
):
    source_date_from, source_date_to = source_dates_for_utc_window(
        onboarding_window["utc_start"],
        onboarding_window["utc_end"],
        mixpanel_timezone(),
        clamp_to_today=True,
    )
    total_views = safe_int(stats.get("total_views"))
    download_rate = (safe_int(downloads) / total_views * 100) if downloads and total_views else None
    reelfarm_materials = safe_int(stats.get("reelfarm_materials") or stats.get("reelfarm_posts"))
    reelfarm_expected_automations = (
        safe_int(reelfarm_expected_count)
        if material_mode == "published_materials"
        else reelfarm_materials
    )
    reelfarm_published_automations = safe_int(
        stats.get("reelfarm_published_automations") or stats.get("reelfarm_posts")
    )
    clone_materials = safe_int(stats.get("clone_materials") or stats.get("clone_posts"))
    reelfarm_posts = safe_int(stats.get("reelfarm_posts"))
    clone_posts = safe_int(stats.get("clone_posts"))
    reelfarm_views = safe_int(stats.get("reelfarm_views"))
    clone_views = safe_int(stats.get("clone_views"))

    return {
        "report_date": window["report_date"],
        "report_timezone": window["report_timezone"],
        "business_window_local": {
            "start": window["start_local"].isoformat(),
            "end": window["end_local"].isoformat(),
        },
        "onboarding_window_local": {
            "start": onboarding_window["start_local"].isoformat(),
            "end": onboarding_window["end_local"].isoformat(),
        },
        "utc_window": {
            "start": window["utc_start"].isoformat(),
            "end": window["utc_end"].isoformat(),
        },
        "onboarding_utc_window": {
            "start": onboarding_window["utc_start"].isoformat(),
            "end": onboarding_window["utc_end"].isoformat(),
        },
        "source_date_from": source_date_from,
        "source_date_to": source_date_to,
        "reelfarm_materials": reelfarm_materials,
        "reelfarm_expected_materials": reelfarm_expected_automations,
        "reelfarm_published_automations": reelfarm_published_automations,
        "reelfarm_expected_automations": reelfarm_expected_automations,
        "reelfarm_posts": reelfarm_posts,
        "reelfarm_views": reelfarm_views,
        "reelfarm_avg_views": (reelfarm_views / reelfarm_posts) if reelfarm_posts else None,
        "clone_materials": clone_materials,
        "clone_expected_materials": clone_materials,
        "clone_posts": clone_posts,
        "clone_views": clone_views,
        "clone_avg_views": (clone_views / clone_posts) if clone_posts else None,
        "total_materials": reelfarm_materials + clone_materials,
        "expected_total_materials": reelfarm_expected_automations + clone_materials,
        "total_posts": reelfarm_posts + clone_posts,
        "total_views": total_views,
        "downloads": downloads,
        "download_rate": download_rate,
        "views_per_download": (total_views / safe_int(downloads)) if downloads else None,
    }


def summarize_business_report_rows(rows):
    total_reelfarm_posts = sum(row["reelfarm_posts"] for row in rows)
    total_clone_posts = sum(row["clone_posts"] for row in rows)
    total_reelfarm_views = sum(row["reelfarm_views"] for row in rows)
    total_clone_views = sum(row["clone_views"] for row in rows)
    total_views = sum(row["total_views"] for row in rows)
    total_downloads = sum(
        safe_int(row["downloads"])
        for row in rows
        if row["downloads"] is not None
    )

    return {
        "reelfarm_materials": sum(row["reelfarm_materials"] for row in rows),
        "reelfarm_expected_materials": sum(row["reelfarm_expected_materials"] for row in rows),
        "reelfarm_published_automations": sum(row["reelfarm_published_automations"] for row in rows),
        "reelfarm_expected_automations": sum(row["reelfarm_expected_automations"] for row in rows),
        "reelfarm_posts": total_reelfarm_posts,
        "reelfarm_views": total_reelfarm_views,
        "reelfarm_avg_views": (total_reelfarm_views / total_reelfarm_posts) if total_reelfarm_posts else None,
        "clone_materials": sum(row["clone_materials"] for row in rows),
        "clone_expected_materials": sum(row["clone_expected_materials"] for row in rows),
        "clone_posts": total_clone_posts,
        "clone_views": total_clone_views,
        "clone_avg_views": (total_clone_views / total_clone_posts) if total_clone_posts else None,
        "total_materials": sum(row["total_materials"] for row in rows),
        "expected_total_materials": sum(row["expected_total_materials"] for row in rows),
        "total_posts": sum(row["total_posts"] for row in rows),
        "total_views": total_views,
        "downloads": total_downloads,
        "download_rate": (total_downloads / total_views * 100) if total_downloads and total_views else None,
    }


def normalize_reelfarm_account_row(row):
    data = dict(row or {})
    int_fields = (
        "automation_count",
        "material_count",
        "post_count",
        "posted_account_count",
        "expected_account_count",
        "total_views",
        "total_likes",
        "total_comments",
        "total_shares",
        "total_bookmarks",
    )
    for field in int_fields:
        data[field] = safe_int(data.get(field))
    data["avg_views"] = (
        data["total_views"] / data["post_count"]
        if data["post_count"]
        else None
    )
    return data


def build_daily_report_product_item(
    product_code,
    product_name,
    report_date,
    row,
    countries=None,
    account_alerts=None,
    mixpanel=None,
):
    row = row or {}
    downloads = row.get("downloads")
    return {
        "product_code": product_code,
        "product_name": product_name,
        "report_date": report_date,
        "reelfarm_views": safe_int(row.get("reelfarm_views")),
        "clone_views": safe_int(row.get("clone_views")),
        "total_views": safe_int(row.get("total_views")),
        "downloads": safe_int(downloads) if downloads is not None else None,
        "download_rate": row.get("download_rate"),
        "total_materials": safe_int(row.get("total_materials")),
        "expected_total_materials": safe_int(
            row.get("expected_total_materials") or row.get("total_materials")
        ),
        "total_posts": safe_int(row.get("total_posts")),
        "reelfarm_posts": safe_int(row.get("reelfarm_posts")),
        "clone_posts": safe_int(row.get("clone_posts")),
        "reelfarm_avg_views": row.get("reelfarm_avg_views"),
        "clone_avg_views": row.get("clone_avg_views"),
        "reelfarm_published_automations": safe_int(row.get("reelfarm_published_automations")),
        "reelfarm_expected_automations": safe_int(row.get("reelfarm_expected_automations")),
        "countries": countries or [],
        "account_alerts": account_alerts or {},
        "mixpanel": mixpanel or {},
    }


def summarize_daily_report_products(products):
    totals = {
        "reelfarm_views": 0,
        "clone_views": 0,
        "total_views": 0,
        "downloads": 0,
        "total_materials": 0,
        "expected_total_materials": 0,
        "total_posts": 0,
        "reelfarm_posts": 0,
        "clone_posts": 0,
        "reelfarm_published_automations": 0,
        "reelfarm_expected_automations": 0,
        "missing_account_count": 0,
        "zero_play_account_count": 0,
    }
    for item in products or []:
        for key in (
            "reelfarm_views",
            "clone_views",
            "total_views",
            "total_materials",
            "expected_total_materials",
            "total_posts",
            "reelfarm_posts",
            "clone_posts",
            "reelfarm_published_automations",
            "reelfarm_expected_automations",
        ):
            totals[key] += safe_int(item.get(key))
        if item.get("downloads") is not None:
            totals["downloads"] += safe_int(item.get("downloads"))
        alerts = item.get("account_alerts") or {}
        totals["missing_account_count"] += safe_int(alerts.get("missing_account_count"))
        totals["zero_play_account_count"] += safe_int(alerts.get("zero_play_account_count"))

    totals["download_rate"] = (
        totals["downloads"] / totals["total_views"] * 100
        if totals["total_views"]
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


def evaluate_sync_readiness(sync_status, required_sources=None, min_finished_at=None):
    required_sources = list(required_sources or ("reelfarm", "museon_clone", "growth_mixpanel"))
    sources = (sync_status or {}).get("sources") if isinstance(sync_status, dict) else {}
    if not isinstance(sources, dict):
        sources = {}
    min_finished = parse_iso_datetime(min_finished_at)
    warnings = []
    source_status = {}
    for source in required_sources:
        item = sources.get(source) or {}
        status = str(item.get("status") or "").strip().lower()
        finished_at = item.get("finished_at")
        finished = parse_iso_datetime(finished_at)
        ok = status == "success" and bool(finished)
        if ok and min_finished and finished < min_finished:
            ok = False
            warnings.append(
                f"{item.get('label') or source} 同步时间早于统计窗口结束：{finished_at or '暂无'}"
            )
        elif not ok:
            label = item.get("label") or source
            if not item:
                warnings.append(f"{label} 暂无同步记录")
            elif status != "success":
                error = item.get("error") or ""
                suffix = f"：{error}" if error else ""
                warnings.append(f"{label} 最近同步状态不是 success（{status or 'unknown'}）{suffix}")
            else:
                warnings.append(f"{label} 最近同步缺少完成时间")
        source_status[source] = {
            "ok": ok,
            "status": item.get("status"),
            "finished_at": finished_at,
            "label": item.get("label") or source,
        }
    return {
        "ok": not warnings,
        "required_sources": required_sources,
        "min_finished_at": min_finished.isoformat() if min_finished else None,
        "warnings": warnings,
        "sources": source_status,
    }
