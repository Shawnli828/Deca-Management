from __future__ import annotations


def bar(value, vmax, width=14):
    if not vmax:
        return "░" * width
    try:
        filled = round((float(value or 0) / float(vmax)) * width)
    except (TypeError, ValueError, ZeroDivisionError):
        filled = 0
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def fmt(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, str):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.1f}"


def markdown(content):
    return {"tag": "div", "text": {"tag": "lark_md", "content": content}}


def hr():
    return {"tag": "hr"}


def kpi3(items):
    return {
        "tag": "column_set",
        "flex_mode": "stretch",
        "background_style": "grey",
        "horizontal_spacing": "small",
        "columns": [
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"<font color='grey'>{label}</font>\n**{value}**" if label else " ",
                    }
                ],
            }
            for label, value in items
        ],
    }


def product_daily_table(data):
    rows = []
    products = data.get("products") or []
    for product in products:
        download = "—" if product.get("onboarding") is None else fmt(product.get("onboarding"))
        download_rate = "—" if product.get("downloadRate") is None else f"{fmt(product.get('downloadRate'))}%"
        rows.append(
            "|{name}|{posts}|{views}|{rf_avg}|{download}|{rate}|".format(
                name=product.get("name") or "Product",
                posts=fmt(product.get("totalPosts")),
                views=fmt(product.get("totalPlays")),
                rf_avg=fmt(product.get("rfAvg")),
                download=download,
                rate=download_rate,
            )
        )
    if not rows:
        rows.append("|暂无产品|—|—|—|—|—|")
    return (
        f"**各 App 当日数据 · {data.get('bizDate') or ''}**\n\n"
        "|App|Post|View|RF Avg View|Download|下载/播放|\n"
        "|:-|-:|-:|-:|-:|-:|\n"
        + "\n".join(rows)
    )


def trend_table(data):
    rows = []
    for item in data.get("trend") or []:
        rows.append(
            "|{date}|{view}|{download}|".format(
                date=item.get("label") or item.get("date") or "—",
                view=fmt(item.get("view")),
                download=fmt(item.get("download")),
            )
        )
    if not rows:
        rows.append("|暂无数据|—|—|")
    return (
        "**View / Download 趋势**\n\n"
        "|日期|累计 View|累计 Download|\n"
        "|:-|-:|-:|\n"
        + "\n".join(rows)
    )


def overview_tab(data):
    return [
        markdown(product_daily_table(data)),
        hr(),
        markdown(trend_table(data)),
    ]


def section_title(title):
    return markdown(f"**{title}**")


def build_webhook_safe_elements(data):
    return overview_tab(data)


def build_daily_report_card(data):
    return {
        "schema": "2.0",
        "config": {"update_multi": True, "wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "Deca Growth 每日业务数据"},
            "subtitle": {
                "tag": "plain_text",
                "content": f"业务日 {data.get('bizDate') or ''} · 内容窗口 {data.get('window') or ''}",
            },
        },
        "body": {"elements": build_webhook_safe_elements(data)},
    }
