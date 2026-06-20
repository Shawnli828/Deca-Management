from datetime import datetime, timezone


DATA_QUERY_RESOURCES = {
    "summary",
    "product_kpis",
    "product_rollups",
    "country_cards",
    "countries",
    "accounts",
    "account_posts",
    "posts",
    "materials",
    "daily_metrics",
    "top_posts",
}
DATA_QUERY_METRICS = {"view_count", "like_count", "comment_count", "share_count", "bookmark_count"}


def data_query_payload(
    query,
    *,
    query_value,
    compact_filters,
    query_filters,
    query_summary,
    query_product_kpis,
    query_product_rollups,
    query_country_cards,
    query_countries,
    query_accounts,
    query_posts,
    query_materials,
    query_daily_metrics,
):
    resource = query_value(query, "resource").lower()
    if resource not in DATA_QUERY_RESOURCES:
        raise ValueError("Unsupported or missing resource.")

    filters = compact_filters(query_filters(query))
    response = {
        "ok": True,
        "resource": resource,
        "filters": filters,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if resource == "summary":
        response["data"] = query_summary(query)
    elif resource == "product_kpis":
        response["data"] = query_product_kpis(query)
    elif resource == "product_rollups":
        response["data"] = query_product_rollups(query)
    elif resource == "country_cards":
        response["data"] = query_country_cards(query)
    elif resource == "countries":
        response["data"] = query_countries(query)
    elif resource == "accounts":
        response["data"] = query_accounts(query)
    elif resource in {"posts", "account_posts"}:
        rows, pagination = query_posts(query)
        response["data"] = rows[: pagination["limit"]]
        response["pagination"] = pagination
    elif resource == "materials":
        rows, pagination = query_materials(query)
        response["data"] = rows[: pagination["limit"]]
        response["pagination"] = pagination
    elif resource == "daily_metrics":
        response["data"] = query_daily_metrics(query)
    elif resource == "top_posts":
        metric = query_value(query, "metric", "view_count")
        if metric not in DATA_QUERY_METRICS:
            raise ValueError("Unsupported metric.")
        filters["metric"] = metric
        rows, pagination = query_posts(query, top_metric=metric)
        response["filters"] = filters
        response["data"] = rows[: pagination["limit"]]
        response["pagination"] = pagination

    return response
