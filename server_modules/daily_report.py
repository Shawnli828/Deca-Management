from datetime import datetime, timedelta, timezone

from server_modules.sync_status import format_sync_readiness_line, format_sync_status_line
from server_modules.time_windows import report_timezone


def default_daily_report_date():
    tz = report_timezone()
    current_local = datetime.now(timezone.utc).astimezone(tz)
    today_start = datetime(current_local.year, current_local.month, current_local.day, tzinfo=tz)
    return (today_start - timedelta(days=1)).date().isoformat()


def format_number_compact(value):
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    abs_number = abs(number)
    if abs_number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs_number >= 1_000:
        return f"{number / 1_000:.1f}K"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.1f}"


def format_percent(value):
    if value is None:
        return "—"
    return f"{float(value):.2f}%"


def daily_account_alert_line(account):
    username = str(account.get("username") or account.get("display_name") or account.get("account_id") or "unknown")
    username = username if username.startswith("@") else f"@{username}"
    country = account.get("country_name") or account.get("country_code") or "-"
    automation_names = account.get("automation_names") or []
    automation = automation_names[0] if automation_names else ""
    if len(automation_names) > 1:
        automation = f"{automation} 等 {len(automation_names)} 个 automation"
    if automation:
        return f"{username}｜{country}｜{automation}"
    return f"{username}｜{country}"


def append_daily_account_alert_lines(lines, alerts, limit=6):
    alerts = alerts or {}
    missing_count = int(alerts.get("missing_account_count") or 0)
    zero_count = int(alerts.get("zero_play_account_count") or 0)
    if not missing_count and not zero_count:
        return
    lines.append("账号异常")
    lines.append(f"- 未发送账号：{missing_count}")
    missing_accounts = alerts.get("missing_accounts") or []
    for account in missing_accounts[:limit]:
        lines.append(f"  - {daily_account_alert_line(account)}")
    missing_left = missing_count - min(len(missing_accounts), limit)
    if missing_left > 0:
        lines.append(f"  - 还有 {missing_left} 个未展示")
    lines.append(f"- 0播警告：{zero_count}")
    zero_play_accounts = alerts.get("zero_play_accounts") or []
    for account in zero_play_accounts[:limit]:
        lines.append(f"  - {daily_account_alert_line(account)}")
    zero_left = zero_count - min(len(zero_play_accounts), limit)
    if zero_left > 0:
        lines.append(f"  - 还有 {zero_left} 个未展示")


def daily_feishu_report_text(report):
    totals = report.get("totals") or {}
    window = report.get("business_window_local") or {}
    onboarding_window = report.get("onboarding_window_local") or {}
    lines = [
        "Deca Growth 每日业务数据",
        f"业务日：{report.get('report_date')}",
        f"内容窗口：{window.get('start', '')} → {window.get('end', '')} BJT",
        f"Onboarding窗口：{onboarding_window.get('start', '')} → {onboarding_window.get('end', '')} BJT",
        format_sync_status_line(report.get("sync_status")),
        format_sync_readiness_line(report.get("sync_ready")),
        "",
        "总览",
        f"- 总播放：{int(totals.get('total_views') or 0):,}",
        f"- ReelFarm：{int(totals.get('reelfarm_views') or 0):,}",
        f"- Clone：{int(totals.get('clone_views') or 0):,}",
        f"- RF发布账号/应发账号：{int(totals.get('reelfarm_published_automations') or 0):,} / {int(totals.get('reelfarm_expected_automations') or 0):,}",
        f"- ReelFarm均播：{format_number_compact(totals.get('reelfarm_avg_views'))}",
        f"- Clone均播：{format_number_compact(totals.get('clone_avg_views'))}",
        f"- Onboarding Unique：{int(totals.get('downloads') or 0):,}",
        f"- 下载/播放：{format_percent(totals.get('download_rate'))}",
        f"- 未发送账号：{int(totals.get('missing_account_count') or 0):,}",
        f"- 0播警告账号：{int(totals.get('zero_play_account_count') or 0):,}",
        "",
    ]

    for item in report.get("products") or []:
        downloads = item.get("downloads")
        countries = item.get("countries") if isinstance(item.get("countries"), list) else []
        lines.extend([
            f"{item.get('product_name')} ({item.get('product_code')})",
            "总览",
            f"- 播放：{int(item.get('total_views') or 0):,} = RF {int(item.get('reelfarm_views') or 0):,} + Clone {int(item.get('clone_views') or 0):,}",
            f"- RF发布账号/应发账号：{int(item.get('reelfarm_published_automations') or 0):,} / {int(item.get('reelfarm_expected_automations') or 0):,}",
            f"- RF总均播：{format_number_compact(item.get('reelfarm_avg_views'))}（Posts {int(item.get('reelfarm_posts') or 0):,}，Views {int(item.get('reelfarm_views') or 0):,}）",
            f"- Clone均播：{format_number_compact(item.get('clone_avg_views'))}（Posts {int(item.get('clone_posts') or 0):,}，Views {int(item.get('clone_views') or 0):,}）",
        ])
        append_daily_account_alert_lines(lines, item.get("account_alerts"))
        lines.append("国家 RF 均播")
        if countries:
            for country in countries:
                lines.append(
                    f"- {country.get('country_name') or country.get('country_code')}："
                    f"{format_number_compact(country.get('reelfarm_avg_views'))}"
                    f"（Posts {int(country.get('reelfarm_posts') or 0):,}，Views {int(country.get('reelfarm_views') or 0):,}）"
                )
        else:
            lines.append("- 暂无 RF 发布数据")
        lines.extend([
            "下载",
            f"- Onboarding Unique：{int(downloads):,}" if downloads is not None else "- Onboarding Unique：未配置/未返回",
            f"- 下载/播放：{format_percent(item.get('download_rate'))}",
            "",
        ])

    errors = report.get("errors") or []
    if errors:
        lines.append("注意")
        for error in errors[:6]:
            lines.append(f"- {error.get('product_code')}: {error.get('error')}")
        if len(errors) > 6:
            lines.append(f"- 还有 {len(errors) - 6} 个错误未展示")

    return "\n".join(lines).strip()
