from datetime import datetime, timezone

from server_modules.common import int_or_none, stable_id
from server_modules.time_windows import BUSINESS_TIMEZONE, parse_iso_datetime


ZERO_PLAY_ISSUE = "0播警告"
ZERO_PLAY_VIEW_THRESHOLD = 150
ZERO_PLAY_POST_LIMIT = 2


def collect_zero_play_issue_candidate(candidates, account_id, published_at, view_count, sync_date):
    """Collect non-current-day posts for the automatic low-view issue check."""
    account_id = str(account_id or "").strip()
    published = parse_iso_datetime(published_at)
    if not account_id or not published:
        return
    if published.astimezone(BUSINESS_TIMEZONE).date().isoformat() >= sync_date:
        return
    candidates.setdefault(account_id, []).append({
        "published_at": published,
        "view_count": int_or_none(view_count),
    })


def apply_zero_play_issues(
    conn,
    candidates,
    synced_at,
    *,
    placeholder,
    upsert_row,
    active_tiktok_automation_account_ids,
):
    now = synced_at or datetime.now(timezone.utc).isoformat()
    for account_id, posts in (candidates or {}).items():
        latest_posts = sorted(
            posts,
            key=lambda item: item.get("published_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[:ZERO_PLAY_POST_LIMIT]
        should_warn = len(latest_posts) == ZERO_PLAY_POST_LIMIT and all(
            item.get("view_count") is not None and item.get("view_count") < ZERO_PLAY_VIEW_THRESHOLD
            for item in latest_posts
        )
        if should_warn:
            upsert_row(
                conn,
                "account_issues",
                {
                    "id": stable_id("account_issue", account_id, ZERO_PLAY_ISSUE.lower()),
                    "account_id": account_id,
                    "issue": ZERO_PLAY_ISSUE,
                    "source": "auto",
                    "created_at": now,
                    "updated_at": now,
                },
                ["account_id", "issue"],
            )
        else:
            conn.execute(
                f"DELETE FROM account_issues WHERE account_id = {placeholder} AND issue = {placeholder} AND COALESCE(source, '') = {placeholder}",
                (account_id, ZERO_PLAY_ISSUE, "auto"),
            )
    cleanup_zero_play_issues_for_non_active_tiktok(
        conn,
        placeholder=placeholder,
        active_tiktok_automation_account_ids=active_tiktok_automation_account_ids,
    )


def cleanup_zero_play_issues_for_non_active_tiktok(
    conn,
    *,
    placeholder,
    active_tiktok_automation_account_ids,
):
    rows = conn.execute(
        f"SELECT account_id FROM account_issues WHERE issue = {placeholder} AND COALESCE(source, '') = {placeholder}",
        (ZERO_PLAY_ISSUE, "auto"),
    ).fetchall()
    ids = [str(dict(row).get("account_id") or "").strip() for row in rows]
    active_ids = active_tiktok_automation_account_ids(conn, ids)
    for account_id in ids:
        if account_id in active_ids:
            continue
        conn.execute(
            f"DELETE FROM account_issues WHERE account_id = {placeholder} AND issue = {placeholder} AND COALESCE(source, '') = {placeholder}",
            (account_id, ZERO_PLAY_ISSUE, "auto"),
        )


def account_issues_payload(
    account_ids,
    *,
    connect_db,
    init_relational_schema,
    placeholder,
    active_tiktok_automation_account_ids,
):
    ids = [str(item or "").strip() for item in account_ids if str(item or "").strip()]
    if not ids:
        return {"ok": True, "issues": {}}
    placeholders = ",".join([placeholder] * len(ids))
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"SELECT account_id, issue FROM account_issues WHERE account_id IN ({placeholders}) ORDER BY issue",
            tuple(ids),
        ).fetchall()
        zero_play_active_ids = active_tiktok_automation_account_ids(conn, ids)
    issues = {}
    for row in rows:
        data = dict(row)
        if data.get("issue") == ZERO_PLAY_ISSUE and data.get("account_id") not in zero_play_active_ids:
            continue
        issues.setdefault(data.get("account_id"), []).append(data.get("issue"))
    return {"ok": True, "issues": issues}


def add_account_issue(
    account_id,
    issue,
    *,
    clean_issue,
    connect_db,
    init_relational_schema,
    upsert_row,
):
    account_id = str(account_id or "").strip()
    issue = clean_issue(issue)
    if not account_id or not issue:
        raise ValueError("account_id and issue are required.")
    now = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        init_relational_schema(conn)
        upsert_row(
            conn,
            "account_issues",
            {
                "id": stable_id("account_issue", account_id, issue.lower()),
                "account_id": account_id,
                "issue": issue,
                "source": "manual",
                "created_at": now,
                "updated_at": now,
            },
            ["account_id", "issue"],
        )
        conn.commit()
    return {"ok": True, "account_id": account_id, "issue": issue}


def delete_account_issue(
    account_id,
    issue,
    *,
    clean_issue,
    connect_db,
    init_relational_schema,
    placeholder,
):
    account_id = str(account_id or "").strip()
    issue = clean_issue(issue)
    if not account_id or not issue:
        raise ValueError("account_id and issue are required.")
    with connect_db() as conn:
        init_relational_schema(conn)
        conn.execute(
            f"DELETE FROM account_issues WHERE account_id = {placeholder} AND issue = {placeholder}",
            (account_id, issue),
        )
        conn.commit()
    return {"ok": True, "account_id": account_id, "issue": issue}


def attach_account_issues(rows, issues_payload):
    ids = [str(row.get("account_id") or "").strip() for row in rows if str(row.get("account_id") or "").strip()]
    issue_map = issues_payload(ids).get("issues", {}) if ids else {}
    for row in rows:
        row["issues"] = issue_map.get(row.get("account_id"), [])
    return rows


def account_alert_display_name(item):
    username = str(item.get("username") or item.get("display_name") or "").strip()
    if username:
        return username
    return str(item.get("reelfarm_account_id") or item.get("account_id") or "Unknown").strip()


def daily_reelfarm_account_alerts(
    product_code,
    utc_start,
    utc_end,
    *,
    limit=120,
    connect_db,
    init_relational_schema,
    placeholder,
    reelfarm_expected_automation_condition,
):
    """Return account-level gaps for the daily RF report."""
    product_code = str(product_code or "").strip().upper()
    if not product_code:
        return {
            "missing_account_count": 0,
            "zero_play_account_count": 0,
            "missing_accounts": [],
            "zero_play_accounts": [],
        }

    utc_start_iso = utc_start.isoformat() if isinstance(utc_start, datetime) else str(utc_start or "")
    utc_end_iso = utc_end.isoformat() if isinstance(utc_end, datetime) else str(utc_end or "")

    with connect_db() as conn:
        init_relational_schema(conn)
        active_rows = conn.execute(
            f"""
            SELECT
                acc.id AS account_id,
                acc.reelfarm_account_id AS reelfarm_account_id,
                acc.username AS username,
                acc.display_name AS display_name,
                m.code AS country_code,
                m.name AS country_name,
                a.id AS automation_id,
                a.reelfarm_automation_id AS reelfarm_automation_id,
                a.name AS automation_name,
                post.id AS post_id,
                mat.id AS material_id,
                COALESCE(post.view_count, 0) AS view_count,
                post.published_at AS published_at
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            JOIN automations a ON a.product_market_channel_id = pmc.id
            JOIN accounts acc ON acc.id = a.account_id
            LEFT JOIN materials mat
              ON mat.automation_id = a.id
             AND mat.created_at >= {placeholder}
             AND mat.created_at < {placeholder}
            LEFT JOIN posts post ON post.material_id = mat.id
            WHERE p.code = {placeholder}
              AND ch.code = {placeholder}
              AND {reelfarm_expected_automation_condition("a")}
            ORDER BY m.code, acc.username, a.name
            """,
            (utc_start_iso, utc_end_iso, product_code, "TIKTOK"),
        ).fetchall()

        issue_rows = conn.execute(
            f"""
            SELECT
                acc.id AS account_id,
                acc.reelfarm_account_id AS reelfarm_account_id,
                acc.username AS username,
                acc.display_name AS display_name,
                m.code AS country_code,
                m.name AS country_name,
                a.id AS automation_id,
                a.reelfarm_automation_id AS reelfarm_automation_id,
                a.name AS automation_name,
                ai.updated_at AS issue_updated_at
            FROM account_issues ai
            JOIN accounts acc ON acc.id = ai.account_id
            JOIN automations a ON a.account_id = acc.id
            JOIN product_market_channels pmc ON pmc.id = acc.product_market_channel_id
            JOIN product_markets pm ON pm.id = pmc.product_market_id
            JOIN products p ON p.id = pm.product_id
            JOIN markets m ON m.id = pm.market_id
            JOIN channels ch ON ch.id = pmc.channel_id
            WHERE ai.issue = {placeholder}
              AND COALESCE(ai.source, '') = {placeholder}
              AND p.code = {placeholder}
              AND ch.code = {placeholder}
              AND {reelfarm_expected_automation_condition("a")}
            ORDER BY m.code, acc.username, a.name
            """,
            (ZERO_PLAY_ISSUE, "auto", product_code, "TIKTOK"),
        ).fetchall()

    accounts = {}
    for row in active_rows:
        item = dict(row)
        account_id = str(item.get("account_id") or "").strip()
        if not account_id:
            continue
        account = accounts.setdefault(account_id, {
            "account_id": account_id,
            "reelfarm_account_id": item.get("reelfarm_account_id"),
            "username": item.get("username"),
            "display_name": item.get("display_name"),
            "country_code": item.get("country_code"),
            "country_name": item.get("country_name"),
            "automation_names": set(),
            "automation_ids": set(),
            "post_ids": set(),
            "material_ids": set(),
            "views_by_post": {},
            "latest_post_at": "",
        })
        if item.get("automation_name"):
            account["automation_names"].add(str(item.get("automation_name")))
        if item.get("automation_id"):
            account["automation_ids"].add(str(item.get("automation_id")))
        if item.get("post_id"):
            post_id = str(item.get("post_id"))
            account["post_ids"].add(post_id)
            account["views_by_post"].setdefault(post_id, int(item.get("view_count") or 0))
            published_at = str(item.get("published_at") or "")
            if published_at and published_at > str(account.get("latest_post_at") or ""):
                account["latest_post_at"] = published_at
        if item.get("material_id"):
            account["material_ids"].add(str(item.get("material_id")))

    missing_accounts = []
    for account in accounts.values():
        if account.get("post_ids"):
            continue
        missing_accounts.append({
            "account_id": account.get("account_id"),
            "reelfarm_account_id": account.get("reelfarm_account_id"),
            "username": account_alert_display_name(account),
            "display_name": account.get("display_name"),
            "country_code": account.get("country_code"),
            "country_name": account.get("country_name"),
            "automation_names": sorted(account.get("automation_names") or []),
            "automation_count": len(account.get("automation_ids") or []),
            "published_count": 0,
            "views": 0,
        })
    missing_accounts.sort(key=lambda item: (
        str(item.get("country_code") or ""),
        str(item.get("username") or ""),
    ))

    zero_accounts = {}
    for row in issue_rows:
        item = dict(row)
        account_id = str(item.get("account_id") or "").strip()
        if not account_id:
            continue
        account = zero_accounts.setdefault(account_id, {
            "account_id": account_id,
            "reelfarm_account_id": item.get("reelfarm_account_id"),
            "username": account_alert_display_name(item),
            "display_name": item.get("display_name"),
            "country_code": item.get("country_code"),
            "country_name": item.get("country_name"),
            "automation_names": set(),
            "issue": ZERO_PLAY_ISSUE,
            "issue_updated_at": item.get("issue_updated_at"),
        })
        if item.get("automation_name"):
            account["automation_names"].add(str(item.get("automation_name")))
    zero_play_accounts = []
    for account in zero_accounts.values():
        account["automation_names"] = sorted(account.get("automation_names") or [])
        zero_play_accounts.append(account)
    zero_play_accounts.sort(key=lambda item: (
        str(item.get("country_code") or ""),
        str(item.get("username") or ""),
    ))

    return {
        "missing_account_count": len(missing_accounts),
        "zero_play_account_count": len(zero_play_accounts),
        "missing_accounts": missing_accounts[:limit],
        "missing_accounts_truncated": max(len(missing_accounts) - limit, 0),
        "zero_play_accounts": zero_play_accounts[:limit],
        "zero_play_accounts_truncated": max(len(zero_play_accounts) - limit, 0),
    }
