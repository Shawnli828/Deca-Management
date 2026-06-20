from datetime import datetime, timedelta, timezone


def beijing_day_window(now=None):
    beijing = timezone(timedelta(hours=8))
    current = now or datetime.now(timezone.utc)
    local = current.astimezone(beijing)
    start_local = datetime(local.year, local.month, local.day, tzinfo=beijing)
    end_local = start_local + timedelta(days=1)
    return {
        "beijing_date": start_local.date().isoformat(),
        "utc_start": start_local.astimezone(timezone.utc).isoformat(),
        "utc_end": end_local.astimezone(timezone.utc).isoformat(),
    }


def product_country_lookup(*, load_data, product_country_lookup_impl):
    return product_country_lookup_impl(load_data())


def publish_check_accounts(
    product_code,
    country_code,
    utc_start,
    utc_end,
    *,
    db_placeholder,
    connect_db,
    init_relational_schema,
    reelfarm_expected_automation_condition,
    row_dict,
):
    placeholder = db_placeholder()
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                acc.id AS account_id,
                acc.reelfarm_account_id,
                acc.username,
                acc.display_name,
                acc.avatar_url,
                acc.status AS account_status,
                a.id AS automation_id,
                a.reelfarm_automation_id,
                a.name AS automation_name,
                a.status AS automation_status,
                COUNT(DISTINCT CASE
                    WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder}
                    THEN post.id
                END) AS published_count,
                MAX(CASE
                    WHEN post.published_at >= {placeholder} AND post.published_at < {placeholder}
                    THEN post.published_at
                END) AS today_latest_post_at,
                MAX(post.published_at) AS latest_post_at
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            JOIN automations a ON a.product_market_channel_id = pmc.id
            LEFT JOIN accounts acc ON acc.id = a.account_id
            LEFT JOIN materials mat ON mat.automation_id = a.id
            LEFT JOIN posts post ON post.material_id = mat.id
            WHERE ch.code = {placeholder}
              AND p.code = {placeholder}
              AND m.code = {placeholder}
              AND {reelfarm_expected_automation_condition("a")}
              AND acc.id IS NOT NULL
            GROUP BY
                acc.id,
                acc.reelfarm_account_id,
                acc.username,
                acc.display_name,
                acc.avatar_url,
                acc.status,
                a.id,
                a.reelfarm_automation_id,
                a.name,
                a.status
            ORDER BY acc.username, a.name
            """,
            (utc_start, utc_end, utc_start, utc_end, "TIKTOK", product_code, country_code),
        ).fetchall()
    return [row_dict(row) for row in rows]


def run_publish_check(*, load_publish_check_state, save_publish_check_state, product_country_lookup, publish_check_accounts):
    state = load_publish_check_state()
    window = beijing_day_window()
    lookup = product_country_lookup()
    groups = []
    totals = {
        "assignments": 0,
        "accounts": 0,
        "published_accounts": 0,
        "missing_accounts": 0,
    }

    for assignment in state.get("assignments", []):
        product_id = str(assignment.get("product_id") or "")
        country_id = str(assignment.get("country_id") or "")
        context = lookup.get((product_id, country_id))
        if not context:
            continue

        product_code = context["product"]["code"]
        country_code = context["country"]["code"]
        accounts = publish_check_accounts(product_code, country_code, window["utc_start"], window["utc_end"])
        missing = [account for account in accounts if int(account.get("published_count") or 0) <= 0]
        published_count = len(accounts) - len(missing)
        group = {
            "assignment_id": assignment.get("id"),
            "person_id": assignment.get("person_id"),
            "person_name": assignment.get("person_name") or "未命名负责人",
            "product": context["product"],
            "country": context["country"],
            "account_count": len(accounts),
            "published_account_count": published_count,
            "missing_account_count": len(missing),
            "missing_accounts": missing,
        }
        groups.append(group)
        totals["assignments"] += 1
        totals["accounts"] += len(accounts)
        totals["published_accounts"] += published_count
        totals["missing_accounts"] += len(missing)

    result = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "beijing_date": window["beijing_date"],
        "utc_window": {"start": window["utc_start"], "end": window["utc_end"]},
        "totals": totals,
        "groups": groups,
    }
    state["last_result"] = result
    save_publish_check_state(state)
    return result


def publish_check_reminder_text(result):
    totals = result.get("totals") if isinstance(result, dict) else {}
    groups = result.get("groups") if isinstance(result, dict) else []
    missing_total = int((totals or {}).get("missing_accounts") or 0)
    beijing_date = result.get("beijing_date") or "未生成日期"
    lines = [
        f"Deca Growth 发布检查提醒",
        f"北京时间日期：{beijing_date}",
        f"未发布账号：{missing_total}",
        "",
    ]
    if missing_total <= 0:
        lines.append("全部负责范围今天都有发布。")
        return "\n".join(lines)

    shown = 0
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, dict):
            continue
        missing_count = int(group.get("missing_account_count") or 0)
        if missing_count <= 0:
            continue
        product = group.get("product") if isinstance(group.get("product"), dict) else {}
        country = group.get("country") if isinstance(group.get("country"), dict) else {}
        lines.append(f"{group.get('person_name') or '未命名负责人'}｜{product.get('name') or '-'} · {country.get('name') or '-'}：{missing_count} 个账号未发布")
        for account in (group.get("missing_accounts") or [])[:8]:
            if not isinstance(account, dict):
                continue
            username = account.get("username") or account.get("display_name") or account.get("reelfarm_account_id") or account.get("account_id") or "unknown"
            automation = account.get("automation_name") or account.get("reelfarm_automation_id") or "无 automation 名称"
            lines.append(f"  - @{str(username).lstrip('@')}｜{automation}")
            shown += 1
        if missing_count > 8:
            lines.append(f"  - 还有 {missing_count - 8} 个账号未展示")
        lines.append("")
        if shown >= 40:
            lines.append("更多未发布账号请打开中台查看。")
            break
    return "\n".join(lines).strip()


def send_publish_check_reminder(*, load_publish_check_state, send_feishu_message):
    state = load_publish_check_state()
    result = state.get("last_result") if isinstance(state, dict) else None
    if not isinstance(result, dict):
        return {"ok": False, "error": "No publish check result yet. Run check first."}
    message = publish_check_reminder_text(result)
    sent = send_feishu_message(message)
    if not sent.get("ok"):
        return sent
    return {
        "ok": True,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "missing_accounts": (result.get("totals") or {}).get("missing_accounts", 0),
        "message_preview": message[:500],
    }
