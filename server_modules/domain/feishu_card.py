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


def overview_tab(data):
    global_data = data.get("global") or {}
    products = data.get("products") or []
    total_play_max = max([float(product.get("totalPlays") or 0) for product in products] or [0])
    plays_lines = [
        f"`{bar(product.get('totalPlays'), total_play_max)}` **{product.get('name')}** {fmt(product.get('totalPlays'))}"
        for product in products
    ]

    avg_products = sorted(products, key=lambda product: float(product.get("rfAvg") or 0), reverse=True)
    avg_max = max([float(product.get("rfAvg") or 0) for product in products] or [0])
    avg_lines = [
        f"`{bar(product.get('rfAvg'), avg_max)}` **{product.get('name')}** {fmt(product.get('rfAvg'))}"
        for product in avg_products
    ]

    onboarding_rows = []
    for product in products:
        download_rate = product.get("downloadRate")
        if download_rate is None:
            conversion = "—"
        elif float(download_rate or 0) >= 0.4:
            conversion = f"<font color='green'>{fmt(download_rate)}%</font>"
        else:
            conversion = f"{fmt(download_rate)}%"
        onboarding = "未配置" if product.get("onboarding") is None else fmt(product.get("onboarding"))
        onboarding_rows.append(f"|{product.get('name')}|{onboarding}|{conversion}|")

    anomaly_rows = []
    total_unsent = 0
    total_zero = 0
    for product in products:
        unsent = int(product.get("unsent") or 0)
        zero_play = int(product.get("zeroPlay") or 0)
        total_unsent += unsent
        total_zero += zero_play
        unsent_value = f"<font color='red'>{unsent}</font>" if unsent else "0"
        zero_value = f"<font color='red'>{zero_play}</font>" if zero_play else "0"
        anomaly_rows.append(f"|{product.get('name')}|{unsent_value}|{zero_value}|")

    return [
        kpi3([
            ["总播放", fmt(global_data.get("totalPlays"))],
            ["RF 总播放", fmt(global_data.get("rfPlays"))],
            ["Clone 总播放", fmt(global_data.get("clonePlays"))],
        ]),
        kpi3([
            ["RF 发布", f"{fmt(global_data.get('rfPublished'))}/{fmt(global_data.get('rfExpected'))}"],
            ["RF 均播", fmt(global_data.get("rfAvg"))],
            ["Clone 均播", fmt(global_data.get("cloneAvg"))],
        ]),
        kpi3([
            ["Onboarding", fmt(global_data.get("onboarding"))],
            ["下载/播放", f"{fmt(global_data.get('downloadRate'))}%"],
            ["", ""],
        ]),
        markdown(f"<font color='red'>**未发送 {total_unsent}　·　0播警告 {total_zero}**</font>"),
        hr(),
        markdown(f"**产品线总播放量**\n{chr(10).join(plays_lines)}"),
        hr(),
        markdown(f"**产品线 RF 均播**\n{chr(10).join(avg_lines)}"),
        hr(),
        markdown(
            "**Onboarding 与下载/播放**\n\n"
            "|产品线|Onboarding|下载/播放|\n|:-|-:|-:|\n"
            + "\n".join(onboarding_rows)
        ),
        hr(),
        markdown(
            "**异常账号分布**\n\n"
            "|产品线|未发送|0播警告|\n|:-|-:|-:|\n"
            + "\n".join(anomaly_rows)
            + f"\n|**合计**|<font color='red'>**{total_unsent}**</font>|<font color='red'>**{total_zero}**</font>|"
        ),
    ]


def product_tab(product):
    download_rate = "—" if product.get("downloadRate") is None else f"{fmt(product.get('downloadRate'))}%"
    onboarding = "未配置" if product.get("onboarding") is None else fmt(product.get("onboarding"))
    country_lines = [
        f"{country.get('flag')} {country.get('name')}　**{fmt(country.get('rfAvg'))}**　<font color='grey'>{fmt(country.get('posts'))} posts</font>"
        for country in product.get("countries") or []
    ]
    if not country_lines:
        country_lines = ["暂无 RF 发布数据"]

    elements = [
        kpi3([
            ["总播放", fmt(product.get("totalPlays"))],
            ["RF 总播放", fmt(product.get("rfPlays"))],
            ["Clone 总播放", fmt(product.get("clonePlays"))],
        ]),
        kpi3([
            ["RF 发布", f"{fmt(product.get('rfPublished'))}/{fmt(product.get('rfExpected'))}"],
            ["RF 均播", fmt(product.get("rfAvg"))],
            ["Clone 均播", fmt(product.get("cloneAvg"))],
        ]),
        kpi3([["Onboarding", onboarding], ["下载/播放", download_rate], ["", ""]]),
        kpi3([["未发送", str(product.get("unsent") or 0)], ["0播警告", str(product.get("zeroPlay") or 0)], ["", ""]]),
        hr(),
        markdown(f"**国家 RF 均播**\n{chr(10).join(country_lines)}"),
    ]

    for group in product.get("anomalyGroups") or []:
        accounts = group.get("accounts") or []
        if not accounts and not group.get("more"):
            continue
        block = (
            f"<font color='red'>**{group.get('title')}**</font>\n"
            + "\n".join(
                f"{account.get('flag')} **{account.get('handle')}**　<font color='grey'>{account.get('batch')}</font>"
                for account in accounts
            )
        ).strip()
        if group.get("more"):
            block += f"\n<font color='orange'>{group.get('more')}</font>"
        elements.extend([hr(), markdown(block)])
    return elements


def build_daily_report_card(data):
    tabs = [
        {"tag": "tab", "title": {"tag": "plain_text", "content": "总览"}, "elements": overview_tab(data)}
    ]
    tabs.extend(
        {
            "tag": "tab",
            "title": {"tag": "plain_text", "content": str(product.get("name") or product.get("code") or "Product")},
            "elements": product_tab(product),
        }
        for product in data.get("products") or []
    )
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
        "body": {"elements": [{"tag": "tab_group", "tabs": tabs}]},
    }
