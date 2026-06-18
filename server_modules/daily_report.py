import json
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


def compact_daily_alert_account(item):
    return {
        "username": item.get("username"),
        "display_name": item.get("display_name"),
        "country_code": item.get("country_code"),
        "country_name": item.get("country_name"),
        "automation_names": (item.get("automation_names") or [])[:3],
    }


def compact_daily_account_alerts(alerts, limit=30):
    alerts = alerts or {}
    missing_accounts = alerts.get("missing_accounts") or []
    zero_play_accounts = alerts.get("zero_play_accounts") or []
    return {
        "missing_account_count": alerts.get("missing_account_count") or 0,
        "missing_accounts": [compact_daily_alert_account(item) for item in missing_accounts[:limit]],
        "missing_accounts_truncated": (alerts.get("missing_accounts_truncated") or 0) + max(len(missing_accounts) - limit, 0),
        "zero_play_account_count": alerts.get("zero_play_account_count") or 0,
        "zero_play_accounts": [compact_daily_alert_account(item) for item in zero_play_accounts[:limit]],
        "zero_play_accounts_truncated": (alerts.get("zero_play_accounts_truncated") or 0) + max(len(zero_play_accounts) - limit, 0),
    }


def compact_daily_feishu_report(report):
    totals = report.get("totals") or {}
    products = []
    for item in report.get("products") or []:
        countries = []
        for country in item.get("countries") or []:
            countries.append({
                "country_code": country.get("country_code"),
                "country_name": country.get("country_name"),
                "reelfarm_posts": country.get("reelfarm_posts"),
                "reelfarm_views": country.get("reelfarm_views"),
                "reelfarm_avg_views": country.get("reelfarm_avg_views"),
            })
        products.append({
            "product_code": item.get("product_code"),
            "product_name": item.get("product_name"),
            "total_views": item.get("total_views"),
            "reelfarm_views": item.get("reelfarm_views"),
            "clone_views": item.get("clone_views"),
            "reelfarm_posts": item.get("reelfarm_posts"),
            "clone_posts": item.get("clone_posts"),
            "reelfarm_avg_views": item.get("reelfarm_avg_views"),
            "clone_avg_views": item.get("clone_avg_views"),
            "reelfarm_published_automations": item.get("reelfarm_published_automations"),
            "reelfarm_expected_automations": item.get("reelfarm_expected_automations"),
            "downloads": item.get("downloads"),
            "download_rate": item.get("download_rate"),
            "account_alerts": compact_daily_account_alerts(item.get("account_alerts")),
            "countries": countries,
        })
    return {
        "report_date": report.get("report_date"),
        "business_window_local": report.get("business_window_local"),
        "onboarding_window_local": report.get("onboarding_window_local"),
        "totals": {
            "total_views": totals.get("total_views"),
            "reelfarm_views": totals.get("reelfarm_views"),
            "clone_views": totals.get("clone_views"),
            "reelfarm_posts": totals.get("reelfarm_posts"),
            "clone_posts": totals.get("clone_posts"),
            "reelfarm_avg_views": totals.get("reelfarm_avg_views"),
            "clone_avg_views": totals.get("clone_avg_views"),
            "reelfarm_published_automations": totals.get("reelfarm_published_automations"),
            "reelfarm_expected_automations": totals.get("reelfarm_expected_automations"),
            "downloads": totals.get("downloads"),
            "download_rate": totals.get("download_rate"),
            "missing_account_count": totals.get("missing_account_count"),
            "zero_play_account_count": totals.get("zero_play_account_count"),
        },
        "products": products,
        "errors": report.get("errors") or [],
    }


def previous_daily_report_date(report_date):
    parsed = datetime.strptime(str(report_date), "%Y-%m-%d").date()
    return (parsed - timedelta(days=1)).isoformat()


def daily_feishu_analysis_prompt(report, previous_report=None):
    context = {
        "current": compact_daily_feishu_report(report),
        "previous": compact_daily_feishu_report(previous_report) if previous_report else None,
    }
    return (
        "你是 Deca Growth 中台的增长运营分析助手。请基于下面的日报 JSON 做一份适合发给团队的中文分析。"
        "不要编造 JSON 里没有的数字。重点回答："
        "1. 今日最重要的结论；"
        "2. RF 发布账号/应发账号是否有缺口，哪些产品需要关注，并点名列出未发送账号；"
        "3. 播放量相比昨日变化，优先判断是 RF/Clone 哪边变化、均播下降、还是国家结构变化；"
        "4. Onboarding Unique 和下载/播放转化是否异常，轻微波动可以说正常；"
        "5. 点名列出 0播警告账号；"
        "6. 明天建议跟进的动作。"
        "如果未发送账号或 0播警告账号太多，每个产品最多列 15 个，并说明还有多少未展示。"
        "如果缺少昨日数据，就只分析当前日报。输出请用短段落和项目符号，控制在 700 字内。\n\n"
        f"{json.dumps(context, ensure_ascii=False, separators=(',', ':'))}"
    )


def daily_feishu_report_text(report, analysis=""):
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

    if analysis:
        lines.extend(["AI 分析", str(analysis).strip(), ""])

    errors = report.get("errors") or []
    if errors:
        lines.append("注意")
        for error in errors[:6]:
            lines.append(f"- {error.get('product_code')}: {error.get('error')}")
        if len(errors) > 6:
            lines.append(f"- 还有 {len(errors) - 6} 个错误未展示")

    return "\n".join(lines).strip()
