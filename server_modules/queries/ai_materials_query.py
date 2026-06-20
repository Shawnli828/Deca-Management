from datetime import datetime, timezone

from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema, using_postgres
from server_modules.data_query_helpers import query_value
from server_modules.queries.read_model_queries import stored_reelfarm_country


def ai_materials_payload(query):
    product_filter = query_value(query, "product_code").upper()
    country_filter = query_value(query, "country_code").upper()
    product_id_filter = query_value(query, "product_id")
    country_id_filter = query_value(query, "country_id")
    synced_only = query_value(query, "synced_only").lower() in {"1", "true", "yes"}
    include_raw = query_value(query, "include_raw").lower() in {"1", "true", "yes"}
    placeholder = db_placeholder()
    where = []
    params = []
    if product_filter:
        where.append(f"p.code = {placeholder}")
        params.append(product_filter)
    if country_filter:
        where.append(f"m.code = {placeholder}")
        params.append(country_filter)
    if product_id_filter:
        where.append(f"p.id = {placeholder}")
        params.append(product_id_filter)
    if country_id_filter:
        where.append(f"m.id = {placeholder}")
        params.append(country_id_filter)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with connect_db() as conn:
        init_relational_schema(conn)
        pairs = conn.execute(
            f"""
            SELECT DISTINCT
                p.id AS product_id,
                p.name AS product_name,
                p.owner_type,
                p.code AS product_code,
                m.id AS market_id,
                m.name AS market_name,
                m.code AS market_code
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            {where_sql}
            ORDER BY p.name, m.code
            """,
            tuple(params),
        ).fetchall()

    countries_payload = []
    product_ids = set()
    totals = {"products": 0, "countries": 0, "creators": 0, "materials": 0, "posts": 0}
    for pair in pairs:
        result = stored_reelfarm_country(pair["product_code"], pair["market_code"])
        cards = result.get("cards", [])
        if synced_only and not cards:
            continue

        creators = []
        country_material_count = 0
        country_post_count = 0
        for card in cards:
            videos = card.get("videos") if isinstance(card.get("videos"), list) else []
            posts = card.get("posts") if isinstance(card.get("posts"), list) else []
            posts_by_video = {str(post.get("video_id")): post for post in posts if isinstance(post, dict)}
            materials = [
                {"video": video, "post": posts_by_video.get(str(video.get("video_id") or video.get("id") or ""))}
                for video in videos
                if isinstance(video, dict)
            ]
            country_material_count += len(materials)
            country_post_count += len(posts)
            creators.append(
                {
                    "account": card.get("account", {}),
                    "automation": card.get("automation", {}),
                    "material_count": len(materials),
                    "post_count": len(posts),
                    "materials": materials,
                }
            )

        product_ids.add(pair["product_id"])
        countries_payload.append(
            {
                "product": {
                    "id": pair["product_id"],
                    "name": pair["product_name"],
                    "folder": pair["owner_type"],
                    "reelFarmCode": pair["product_code"],
                },
                "country": {
                    "id": pair["market_id"],
                    "name": pair["market_name"],
                    "reelFarmCode": pair["market_code"],
                },
                "automation_prefix": f"{pair['market_code']}-{pair['product_code']}",
                "synced_at": None,
                "creator_count": len(creators),
                "material_count": country_material_count,
                "post_count": country_post_count,
                "creators": creators,
            }
        )
        totals["countries"] += 1
        totals["creators"] += len(creators)
        totals["materials"] += country_material_count
        totals["posts"] += country_post_count

    totals["products"] = len(product_ids)

    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_backend": "postgres" if using_postgres() else "sqlite",
        "filters": {
            "product_code": product_filter or None,
            "country_code": country_filter or None,
            "product_id": product_id_filter or None,
            "country_id": country_id_filter or None,
            "synced_only": synced_only,
            "include_raw": include_raw,
            "source": "relational",
        },
        "totals": totals,
        "countries": countries_payload,
    }
