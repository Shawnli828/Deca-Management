from datetime import datetime, timedelta


def material_daily_stats_from_rows(rows, parse_iso_datetime, business_material_date_for_utc_datetime):
    daily = {}
    for item in rows:
        source_key = "clone" if item.get("channel_code") == "MUSEON_CLONE" else "reelfarm"
        source_at = item.get("published_at") if source_key == "clone" else item.get("material_created_at")
        report_date = business_material_date_for_utc_datetime(parse_iso_datetime(source_at))
        if not report_date:
            continue
        entry = daily.setdefault(report_date, {
            "reelfarm_materials": set(),
            "clone_materials": set(),
            "reelfarm_posted_materials": set(),
            "reelfarm_published_automations": set(),
            "clone_posts": set(),
            "reelfarm_views": 0,
            "clone_views": 0,
        })
        material_id = item.get("material_id") or item.get("post_id")
        if source_key == "clone":
            if material_id:
                entry["clone_materials"].add(str(material_id))
            if item.get("post_id"):
                entry["clone_posts"].add(str(item.get("post_id")))
            entry["clone_views"] += int(item.get("view_count") or 0)
        else:
            if material_id:
                entry["reelfarm_materials"].add(str(material_id))
            if item.get("post_id"):
                if material_id:
                    entry["reelfarm_posted_materials"].add(str(material_id))
                published_identity = item.get("account_id") or item.get("automation_id")
                if published_identity:
                    entry["reelfarm_published_automations"].add(str(published_identity))
                entry["reelfarm_views"] += int(item.get("view_count") or 0)
    normalized = {}
    for report_date, item in daily.items():
        reelfarm_materials = len(item.get("reelfarm_materials") or set())
        clone_materials = len(item.get("clone_materials") or set())
        reelfarm_posts = len(item.get("reelfarm_posted_materials") or set())
        reelfarm_published_automations = len(item.get("reelfarm_published_automations") or set())
        clone_posts = len(item.get("clone_posts") or set())
        reelfarm_views = int(item.get("reelfarm_views") or 0)
        clone_views = int(item.get("clone_views") or 0)
        normalized[report_date] = {
            "reelfarm_materials": reelfarm_materials,
            "clone_materials": clone_materials,
            "total_materials": reelfarm_materials + clone_materials,
            "reelfarm_posts": reelfarm_posts,
            "reelfarm_published_automations": reelfarm_published_automations,
            "clone_posts": clone_posts,
            "total_posts": reelfarm_posts + clone_posts,
            "reelfarm_views": reelfarm_views,
            "clone_views": clone_views,
            "total_views": reelfarm_views + clone_views,
            "reelfarm_avg_views": (reelfarm_views / reelfarm_posts) if reelfarm_posts else None,
            "clone_avg_views": (clone_views / clone_posts) if clone_posts else None,
        }
    return normalized


def business_growth_daily_stats_from_snapshots(windows, snapshot_cache):
    daily = {}
    for window in windows:
        report_date = str(window["report_date"])
        previous_date = (datetime.strptime(report_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
        current = snapshot_cache.get(report_date, {})
        previous = snapshot_cache.get(previous_date, {})
        entry = {
            "reelfarm_posts": 0,
            "clone_posts": 0,
            "reelfarm_views": 0,
            "clone_views": 0,
        }
        for source, view_key, post_key in (
            ("reelfarm", "reelfarm_views", "reelfarm_posts"),
            ("clone", "clone_views", "clone_posts"),
        ):
            current_posts = current.get(source, {})
            previous_posts = previous.get(source, {})
            for post_id, current_views in current_posts.items():
                previous_views = int(previous_posts.get(post_id) or 0)
                delta = int(current_views or 0) - previous_views
                if delta < 0:
                    delta = 0
                if delta > 0:
                    entry[post_key] += 1
                    entry[view_key] += delta
        entry["total_posts"] = entry["reelfarm_posts"] + entry["clone_posts"]
        entry["total_views"] = entry["reelfarm_views"] + entry["clone_views"]
        daily[report_date] = entry
    return daily
