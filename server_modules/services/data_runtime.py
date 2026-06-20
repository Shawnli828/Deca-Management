from server_modules.app_runtime import (
    connect_db,
    database_snapshot,
    default_data,
    init_relational_schema,
    load_data,
    save_data,
    using_postgres,
)
from server_modules.queries.ai_materials_query import ai_materials_payload as ai_materials_payload_impl
from server_modules.schema import relational_table_counts
from server_modules.services.data_enrichment import enrich_data_with_relational_rollups
from server_modules.services.data_query_runtime import data_query_payload as data_query_payload_impl


def enriched_data(data=None):
    return enrich_data_with_relational_rollups(load_data() if data is None else data)


def reset_data():
    data = default_data()
    save_data(data)
    return enriched_data(data)


def data_query_payload(query):
    return data_query_payload_impl(query)


def ai_materials_payload(query):
    return ai_materials_payload_impl(query)


def growth_dashboard_payload(query):
    from server import growth_dashboard_payload as payload

    return payload(query)


def business_material_report_payload(query):
    from server import business_material_report_payload as payload

    return payload(query)


def sync_product_growth_snapshots(product_code, days):
    from server import sync_product_growth_snapshots as sync_product

    return sync_product(product_code, days)
