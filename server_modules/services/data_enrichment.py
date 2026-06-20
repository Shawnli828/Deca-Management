import json
import re

from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema
from server_modules.product_config import country_code_for, product_code_for
from server_modules.reelfarm_utils import reelfarm_dashboard_automation_condition


def normalized_catalog_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def relational_catalog_code_maps():
    product_codes_by_name = {}
    market_codes_by_product_and_name = {}
    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            """
            SELECT DISTINCT
                p.code AS product_code,
                p.name AS product_name,
                m.code AS market_code,
                m.name AS market_name
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            WHERE ch.code = 'TIKTOK'
            """
        ).fetchall()
    for row in rows:
        product_code = str(row["product_code"] or "").upper()
        market_code = str(row["market_code"] or "").upper()
        product_name_key = normalized_catalog_name(row["product_name"])
        market_name_key = normalized_catalog_name(row["market_name"])
        if product_code and product_name_key:
            product_codes_by_name[product_name_key] = product_code
        if product_code and market_code and market_name_key:
            market_codes_by_product_and_name[(product_code, market_name_key)] = market_code
    return product_codes_by_name, market_codes_by_product_and_name


def enrich_data_with_relational_rollups(data):
    if not isinstance(data, list):
        return data

    enriched = json.loads(json.dumps(data, ensure_ascii=False))
    product_codes_by_name, market_codes_by_product_and_name = relational_catalog_code_maps()
    rollups = {}
    product_rollups = {}
    placeholder = db_placeholder()

    with connect_db() as conn:
        init_relational_schema(conn)
        rows = conn.execute(
            f"""
            SELECT
                p.code AS product_code,
                m.code AS market_code,
                COUNT(DISTINCT acc.id) AS creator_count,
                COUNT(DISTINCT a.id) AS automation_count,
                COUNT(DISTINCT mat.id) AS material_count,
                COUNT(DISTINCT post.id) AS post_count,
                MAX(COALESCE(post.synced_at, mat.synced_at, a.synced_at)) AS last_synced_at
            FROM products p
            JOIN product_markets pm ON pm.product_id = p.id
            JOIN markets m ON m.id = pm.market_id
            JOIN product_market_channels pmc ON pmc.product_market_id = pm.id
            JOIN channels ch ON ch.id = pmc.channel_id
            LEFT JOIN automations a ON a.product_market_channel_id = pmc.id
            LEFT JOIN accounts acc ON acc.id = a.account_id
            LEFT JOIN materials mat ON mat.automation_id = a.id
            LEFT JOIN posts post ON post.material_id = mat.id
            WHERE ch.code = {placeholder}
              AND {reelfarm_dashboard_automation_condition("a")}
            GROUP BY p.code, m.code
            """,
            ("TIKTOK",),
        ).fetchall()

    for row in rows:
        product_code = str(row["product_code"] or "").upper()
        market_code = str(row["market_code"] or "").upper()
        item = {
            "creatorCount": int(row["creator_count"] or 0),
            "automationCount": int(row["automation_count"] or 0),
            "materialCount": int(row["material_count"] or 0),
            "postCount": int(row["post_count"] or 0),
            "reelFarmSyncedAt": row["last_synced_at"] or "",
        }
        rollups[(product_code, market_code)] = item
        product_rollup = product_rollups.setdefault(
            product_code,
            {"creatorCount": 0, "automationCount": 0, "materialCount": 0, "postCount": 0},
        )
        for key in ("creatorCount", "automationCount", "materialCount", "postCount"):
            product_rollup[key] += item[key]

    for product in enriched:
        if not isinstance(product, dict):
            continue
        configured_product_code = product_code_for(product)
        relational_product_code = product_codes_by_name.get(normalized_catalog_name(product.get("name")))
        product_code = configured_product_code
        if relational_product_code and (
            not product.get("reelFarmCode") or configured_product_code not in product_rollups
        ):
            product_code = relational_product_code
            product["reelFarmCode"] = relational_product_code
        product.update(product_rollups.get(product_code, {
            "creatorCount": 0,
            "automationCount": 0,
            "materialCount": 0,
            "postCount": 0,
        }))
        product["countryCount"] = len(product.get("countries", []) or [])
        for country in product.get("countries", []) or []:
            if not isinstance(country, dict):
                continue
            configured_market_code = country_code_for(country)
            relational_market_code = market_codes_by_product_and_name.get(
                (product_code, normalized_catalog_name(country.get("name")))
            )
            market_code = configured_market_code
            if relational_market_code and (
                not country.get("reelFarmCode") or (product_code, configured_market_code) not in rollups
            ):
                market_code = relational_market_code
                country["reelFarmCode"] = relational_market_code
            country.update(rollups.get((product_code, market_code), {
                "creatorCount": 0,
                "automationCount": 0,
                "materialCount": 0,
                "postCount": 0,
            }))

    return enriched
