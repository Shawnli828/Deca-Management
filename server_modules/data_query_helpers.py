import re
from datetime import datetime, timedelta, timezone


def query_value(query, key, default=""):
    value = query.get(key, [default])
    if isinstance(value, list):
        return str(value[0] if value else default).strip()
    return str(value or default).strip()


def query_limit_offset(query, default=50, max_limit=500):
    try:
        limit = int(query_value(query, "limit", default))
    except ValueError:
        limit = default
    try:
        offset = int(query_value(query, "offset", 0))
    except ValueError:
        offset = 0
    limit = max(1, min(max_limit, limit))
    offset = max(0, offset)
    return limit, offset


def query_days_window(query):
    try:
        days = int(query_value(query, "days", 0))
    except ValueError:
        days = 0
    if days <= 0:
        return "", ""
    days = min(days, 366)
    beijing = timezone(timedelta(hours=8))
    current = datetime.now(timezone.utc).astimezone(beijing)
    today_start_local = datetime(current.year, current.month, current.day, tzinfo=beijing)
    start_local = today_start_local - timedelta(days=days)
    end_local = today_start_local
    return start_local.astimezone(timezone.utc).isoformat(), end_local.astimezone(timezone.utc).isoformat()


def query_days_snapshot_window(query):
    try:
        days = int(query_value(query, "days", 0))
    except ValueError:
        days = 0
    if days <= 0:
        return "", ""
    days = min(days, 366)
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def post_datetime_bound(value, end=False, *, business_material_day_window):
    clean = str(value or "").strip()
    if not clean:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean):
        try:
            window = business_material_day_window(clean)
        except ValueError:
            return f"{clean}T23:59:59.999999+00:00" if end else f"{clean}T00:00:00+00:00"
        bound = window["utc_end"] - timedelta(microseconds=1) if end else window["utc_start"]
        return bound.isoformat()
    return clean


def query_filters(query):
    product_code = query_value(query, "product_code").upper()
    market_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    return {
        "product_code": product_code or None,
        "country_code": market_code or None,
        "market_code": market_code or None,
        "account_id": query_value(query, "account_id") or None,
        "automation_id": query_value(query, "automation_id") or None,
        "material_id": query_value(query, "material_id") or None,
        "post_id": query_value(query, "post_id") or None,
        "date_from": query_value(query, "date_from") or None,
        "date_to": query_value(query, "date_to") or None,
        "days": query_value(query, "days") or None,
        "metric": query_value(query, "metric") or None,
        "include": query_value(query, "include") or None,
    }


def compact_filters(filters):
    return {key: value for key, value in filters.items() if value not in ("", None)}


def pagination_payload(limit, offset, rows, total=None):
    total_value = int(total if total is not None else max(offset + min(len(rows), limit), offset + limit + (1 if len(rows) > limit else 0)))
    return {
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total_value,
        "total": total_value,
    }


def row_dict(row):
    return dict(row) if row else {}


def common_where(
    query,
    date_column="post.published_at",
    include_post_dates=True,
    *,
    placeholder,
    data_source_channel_code,
    business_material_day_window,
):
    where = ["ch.code = " + placeholder]
    params = [data_source_channel_code(query_value(query, "source"))]
    product_code = query_value(query, "product_code").upper()
    market_code = (query_value(query, "country_code") or query_value(query, "market_code")).upper()
    account_id = query_value(query, "account_id")
    automation_id = query_value(query, "automation_id")
    material_id = query_value(query, "material_id")
    post_id = query_value(query, "post_id")
    date_from = query_value(query, "date_from")
    date_to = query_value(query, "date_to")
    if include_post_dates and not date_from and not date_to:
        date_from, date_to = query_days_window(query)

    if product_code:
        where.append("p.code = " + placeholder)
        params.append(product_code)
    if market_code:
        where.append("m.code = " + placeholder)
        params.append(market_code)
    if account_id:
        where.append(f"(acc.id = {placeholder} OR acc.reelfarm_account_id = {placeholder} OR acc.username = {placeholder})")
        params.extend([account_id, account_id, account_id.lstrip("@")])
    if automation_id:
        where.append(f"(a.id = {placeholder} OR a.reelfarm_automation_id = {placeholder})")
        params.extend([automation_id, automation_id])
    if material_id:
        where.append(f"(mat.id = {placeholder} OR mat.reelfarm_video_id = {placeholder})")
        params.extend([material_id, material_id])
    if post_id:
        where.append(f"(post.id = {placeholder} OR post.reelfarm_post_id = {placeholder})")
        params.extend([post_id, post_id])
    if include_post_dates and date_from:
        where.append(f"{date_column} >= {placeholder}")
        params.append(post_datetime_bound(date_from, business_material_day_window=business_material_day_window))
    if include_post_dates and date_to:
        where.append(f"{date_column} <= {placeholder}")
        params.append(post_datetime_bound(date_to, end=True, business_material_day_window=business_material_day_window))

    return " AND ".join(where), params


def relational_base_from():
    return """
        FROM products p
        JOIN product_markets pm ON pm.product_id = p.id
        JOIN markets m ON m.id = pm.market_id
        JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
        JOIN channels ch ON ch.id = pmc.channel_id
        LEFT JOIN automations a ON a.product_market_channel_id = pmc.id
        LEFT JOIN accounts acc ON acc.id = a.account_id
        LEFT JOIN materials mat ON mat.automation_id = a.id
        LEFT JOIN posts post ON post.material_id = mat.id
    """
