from datetime import datetime, timezone

from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema, load_data, save_data
from server_modules.automation_naming import build_automation_prefix, build_country_automation_prefix, prefixes_equivalent
from server_modules.common import stable_id
from server_modules.db_core import upsert_row as upsert_row_impl
from server_modules.product_config import (
    configured_product_codes as configured_product_codes_impl,
    country_code_for,
    product_code_for,
)
from server_modules.reelfarm_lifecycle import cleanup_reelfarm_product_from_latest_automations as cleanup_reelfarm_product_from_latest_automations_impl
from server_modules.services import growth_runtime
from server_modules.services import museon_runtime
from server_modules.services import reelfarm_projection_runtime
from server_modules.services import reelfarm_runtime
from server_modules.sync_orchestrator import (
    sync_all_growth_snapshots as sync_all_growth_snapshots_impl,
    sync_all_museon_clone_records as sync_all_museon_clone_records_impl,
    sync_all_reelfarm_records as sync_all_reelfarm_records_impl,
    sync_daily_all_records as sync_daily_all_records_impl,
)
from server_modules.sync_status import (
    compact_sync_run_meta,
    record_sync_run_in_db,
    sync_run_records_count,
)


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


def record_sync_run(source, status, started_at, finished_at=None, duration_seconds=None, product_code="", country_code="", records_count=0, error="", meta=None):
    return record_sync_run_in_db(
        source,
        status,
        started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        product_code=product_code,
        country_code=country_code,
        records_count=records_count,
        error=error,
        meta=meta,
        stable_id_fn=stable_id,
        connect_db_fn=connect_db,
        init_schema_fn=init_relational_schema,
        upsert_row_fn=upsert_row,
        now_fn=datetime.now,
    )


def safe_record_sync_run(*args, **kwargs):
    try:
        return record_sync_run(*args, **kwargs)
    except Exception as error:
        return {"error": str(error)}


def project_synced_country_to_relational(product, country):
    return reelfarm_projection_runtime.project_synced_country_to_relational(product, country)


def cleanup_reelfarm_product_from_latest_automations(product_code, automations, synced_at):
    return cleanup_reelfarm_product_from_latest_automations_impl(
        product_code,
        automations,
        synced_at,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def sync_all_reelfarm_records():
    return sync_all_reelfarm_records_impl(
        reelfarm_api_key=reelfarm_runtime.api_key,
        load_data=load_data,
        save_data=save_data,
        reelfarm_fetch_automations=reelfarm_runtime.fetch_automations,
        product_code_for=product_code_for,
        build_country_automation_prefix=build_country_automation_prefix,
        reelfarm_matches=reelfarm_runtime.matches_from_automations,
        reelfarm_creator_count=reelfarm_runtime.creator_count,
        reelfarm_material_count=reelfarm_runtime.material_count,
        project_synced_country_to_relational=project_synced_country_to_relational,
        cleanup_reelfarm_product_from_latest_automations=cleanup_reelfarm_product_from_latest_automations,
    )


def sync_reelfarm_country(prefix, product_id="", country_id="", product_code="", country_code=""):
    clean_prefix = (prefix or "").strip()
    if not clean_prefix:
        raise ValueError("Missing automation prefix.")

    data = load_data()
    synced_at = datetime.now(timezone.utc).isoformat()
    automations = reelfarm_runtime.fetch_automations()

    for product in data:
        for country in product.get("countries", []) or []:
            id_match = (
                country_id
                and product_id
                and str(country.get("id")) == str(country_id)
                and str(product.get("id")) == str(product_id)
            )
            prefix_match = prefixes_equivalent(build_country_automation_prefix(product, country), clean_prefix)
            if not id_match and not prefix_match:
                continue

            if product_code:
                product["reelFarmCode"] = str(product_code).strip().upper()
            if country_code:
                country["reelFarmCode"] = str(country_code).strip().upper()

            result = reelfarm_runtime.matches_from_automations(clean_prefix, automations=automations)
            country["reelFarmSyncedAt"] = synced_at
            country["creatorCount"] = reelfarm_runtime.creator_count(result)
            country["materialCount"] = reelfarm_runtime.material_count(result)
            scoped_country = dict(country)
            scoped_country["reelFarmResult"] = result
            relational_projection = project_synced_country_to_relational(product, scoped_country)
            effective_product_code = product_code_for(product)
            product_cleanup = cleanup_reelfarm_product_from_latest_automations(
                effective_product_code,
                automations,
                synced_at,
            )
            save_data(data)
            return {
                "ok": True,
                "prefix": clean_prefix,
                "synced_at": synced_at,
                "creator_count": country["creatorCount"],
                "material_count": country["materialCount"],
                "product_cleanup": product_cleanup,
                "relational_projection": relational_projection,
            }

    raise ValueError("No matching country found for this prefix.")


def sync_reelfarm_prefix(prefix, product_id="", country_id="", concept_id="", product_code="", country_code=""):
    clean_prefix = (prefix or "").strip()
    if not clean_prefix:
        raise ValueError("Missing automation prefix.")

    data = load_data()
    synced_at = datetime.now(timezone.utc).isoformat()

    for product in data:
        for country in product.get("countries", []) or []:
            for concept in country.get("concepts", []) or []:
                id_match = (
                    concept_id
                    and country_id
                    and product_id
                    and str(concept.get("id")) == str(concept_id)
                    and str(country.get("id")) == str(country_id)
                    and str(product.get("id")) == str(product_id)
                )
                prefix_match = prefixes_equivalent(build_automation_prefix(product, country, concept), clean_prefix)
                if not id_match and not prefix_match:
                    continue

                if product_code:
                    product["reelFarmCode"] = str(product_code).strip().upper()
                if country_code:
                    country["reelFarmCode"] = str(country_code).strip().upper()
                result = reelfarm_runtime.matches(clean_prefix)
                concept["reelFarmSyncedAt"] = synced_at
                concept["count"] = reelfarm_runtime.creator_count(result)
                save_data(data)
                return {
                    "ok": True,
                    "prefix": clean_prefix,
                    "synced_at": synced_at,
                    "creator_count": concept["count"],
                }

    raise ValueError("No matching Format found for this prefix.")


def sync_museon_clone_country(product_id="", country_id="", product_code="", country_code=""):
    return museon_runtime.sync_clone_country(product_id, country_id, product_code, country_code)


def sync_product_growth_snapshots(product_code, days=30):
    return growth_runtime.sync_product_growth_snapshots(product_code, days)


def configured_product_codes():
    return configured_product_codes_impl(load_data())


def sync_all_museon_clone_records():
    return sync_all_museon_clone_records_impl(
        load_data=load_data,
        product_code_for=product_code_for,
        country_code_for=country_code_for,
        sync_museon_clone_country=sync_museon_clone_country,
    )


def sync_all_growth_snapshots(days=30):
    return sync_all_growth_snapshots_impl(
        configured_product_codes=configured_product_codes,
        sync_product_growth_snapshots=sync_product_growth_snapshots,
        days=days,
    )


def sync_daily_all_records(days=30):
    return sync_daily_all_records_impl(
        days,
        sync_all_reelfarm_records=sync_all_reelfarm_records,
        sync_all_museon_clone_records=sync_all_museon_clone_records,
        sync_all_growth_snapshots=sync_all_growth_snapshots,
        safe_record_sync_run=safe_record_sync_run,
        sync_run_records_count=sync_run_records_count,
        compact_sync_run_meta=compact_sync_run_meta,
    )
