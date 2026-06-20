from datetime import datetime, timezone

from server_modules.account_issues import (
    collect_zero_play_issue_candidate,
)
from server_modules.app_runtime import (
    connect_db,
    db_placeholder,
    init_relational_schema,
    load_data,
    using_postgres,
)
from server_modules.common import stable_id, utc_snapshot_date
from server_modules.domain.reelfarm_projection import (
    card_projection,
    configured_concept_format_projections,
    material_projection,
    post_projection,
)
from server_modules.product_config import country_code_for, product_code_for
from server_modules.repositories.reelfarm_projection_repository import ReelFarmProjectionRepository
from server_modules.time_windows import business_date_string


def project_products_to_relational(data=None, product_code_filter="", market_code_filter=""):
    data = data if isinstance(data, list) else load_data()
    now = datetime.now(timezone.utc).isoformat()
    channel_id = stable_id("channel", "TIKTOK")
    product_code_filter = str(product_code_filter or "").strip().upper()
    market_code_filter = str(market_code_filter or "").strip().upper()

    with connect_db() as conn:
        init_relational_schema(conn)
        repo = ReelFarmProjectionRepository(conn, placeholder=db_placeholder())
        zero_play_candidates = {}
        repo.upsert_row(
            "channels",
            {"id": channel_id, "name": "TikTok", "code": "TIKTOK"},
            ["code"],
        )

        for product in data:
            if not isinstance(product, dict):
                continue

            product_id = str(product.get("id") or stable_id("product", product.get("name")))
            product_code = product_code_for(product)
            if product_code_filter and product_code != product_code_filter:
                continue

            repo.upsert_row(
                "products",
                {
                    "id": product_id,
                    "name": str(product.get("name") or "Untitled Product"),
                    "code": product_code,
                    "owner_type": product.get("folder") or product.get("owner_type"),
                    "logo_url": product.get("logo") or "",
                    "created_at": product.get("created_at") or now,
                    "updated_at": now,
                },
                ["id"],
            )

            for country in product.get("countries", []) or []:
                if not isinstance(country, dict):
                    continue

                market_code = country_code_for(country)
                if market_code_filter and market_code != market_code_filter:
                    continue

                market_id = stable_id("market", market_code)
                product_market_id = stable_id("product_market", product_id, market_id)
                product_market_channel_id = stable_id("product_market_channel", product_market_id, channel_id)

                repo.upsert_row(
                    "markets",
                    {"id": market_id, "name": str(country.get("name") or market_code), "code": market_code},
                    ["code"],
                )
                repo.upsert_row(
                    "product_markets",
                    {"id": product_market_id, "product_id": product_id, "market_id": market_id},
                    ["product_id", "market_id"],
                )
                repo.upsert_row(
                    "product_market_channels",
                    {
                        "id": product_market_channel_id,
                        "product_market_id": product_market_id,
                        "channel_id": channel_id,
                    },
                    ["product_market_id", "channel_id"],
                )

                for concept_format in configured_concept_format_projections(product_id, country.get("concepts", [])):
                    repo.upsert_row(
                        "concepts",
                        concept_format["concept_row"],
                        ["product_id", "name"],
                    )
                    repo.upsert_row(
                        "formats",
                        concept_format["format_row"],
                        ["concept_id", "name"],
                    )

                reel_farm_result = country.get("reelFarmResult")
                has_reelfarm_result = isinstance(reel_farm_result, dict)
                result = reel_farm_result if has_reelfarm_result else {}
                synced_at = country.get("reelFarmSyncedAt") or now
                seen_reelfarm_automation_ids = set()
                for card in result.get("cards", []) or []:
                    projected_card = card_projection(
                        card,
                        product_id=product_id,
                        product_market_channel_id=product_market_channel_id,
                        product_code=product_code,
                        market_code=market_code,
                        synced_at=synced_at,
                    )
                    if not projected_card:
                        continue

                    seen_reelfarm_automation_ids.add(projected_card["automation_reelfarm_id"])
                    if projected_card["is_active_tiktok_automation"]:
                        zero_play_candidates.setdefault(projected_card["account_id"], [])

                    repo.upsert_row(
                        "accounts",
                        projected_card["account_row"],
                        ["product_market_channel_id", "reelfarm_account_id"],
                    )
                    repo.upsert_row(
                        "automations",
                        projected_card["automation_row"],
                        ["reelfarm_automation_id"],
                    )

                    if projected_card["concept_row"] and projected_card["format_row"]:
                        repo.upsert_row(
                            "concepts",
                            projected_card["concept_row"],
                            ["product_id", "name"],
                        )
                        repo.upsert_row(
                            "formats",
                            projected_card["format_row"],
                            ["concept_id", "name"],
                        )

                    for video in projected_card["videos"]:
                        material = material_projection(
                            video,
                            card=projected_card,
                            product_market_channel_id=product_market_channel_id,
                            synced_at=synced_at,
                        )
                        if not material:
                            continue
                        repo.upsert_row(
                            "materials",
                            material["row"],
                            ["reelfarm_video_id"],
                        )

                        post = projected_card["posts_by_video"].get(material["reelfarm_video_id"])
                        projected_post = post_projection(
                            post,
                            material_id=material["material_id"],
                            account_id=projected_card["account_id"],
                            synced_at=synced_at,
                            snapshot_date=utc_snapshot_date(),
                        )
                        if not projected_post:
                            continue
                        if projected_card["is_active_tiktok_automation"]:
                            collect_zero_play_issue_candidate(
                                zero_play_candidates,
                                projected_card["account_id"],
                                post.get("published_at"),
                                post.get("view_count"),
                                business_date_string(synced_at),
                            )
                        repo.upsert_row(
                            "posts",
                            projected_post["post_row"],
                            ["reelfarm_post_id"],
                        )
                        repo.upsert_row(
                            "post_daily_snapshots",
                            projected_post["snapshot_row"],
                            ["post_id", "snapshot_date"],
                        )

                if has_reelfarm_result:
                    repo.mark_missing_reelfarm_automations(
                        product_market_channel_id,
                        seen_reelfarm_automation_ids,
                        synced_at,
                    )

        repo.apply_zero_play_issues(zero_play_candidates, now)
        counts = repo.table_counts()
        conn.commit()

    return {
        "ok": True,
        "projected_at": now,
        "database_backend": "postgres" if using_postgres() else "sqlite",
        "filters": {
            "product_code": product_code_filter or None,
            "market_code": market_code_filter or None,
        },
        "tables": counts,
    }


def project_synced_country_to_relational(product, country):
    if not isinstance(product, dict) or not isinstance(country, dict):
        return None

    scoped_product = dict(product)
    scoped_country = dict(country)
    scoped_product["countries"] = [scoped_country]
    product_code = product_code_for(scoped_product)
    market_code = country_code_for(scoped_country)
    return project_products_to_relational(
        data=[scoped_product],
        product_code_filter=product_code,
        market_code_filter=market_code,
    )
