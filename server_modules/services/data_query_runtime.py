from server_modules.app_runtime import (
    connect_db,
    data_source_channel_code,
    db_placeholder,
    init_relational_schema,
    using_postgres,
)
from server_modules.data_query_helpers import (
    common_where as common_where_impl,
    compact_filters,
    pagination_payload,
    post_datetime_bound as post_datetime_bound_impl,
    query_days_snapshot_window,
    query_days_window,
    query_filters,
    query_limit_offset,
    query_value,
    relational_base_from,
    row_dict,
)
from server_modules.data_query_router import data_query_payload as data_query_payload_impl
from server_modules.detailed_rows import detailed_row, detailed_select
from server_modules.metrics_service import normalize_reelfarm_account_row
from server_modules.queries.account_queries import query_reelfarm_accounts as query_reelfarm_accounts_impl
from server_modules.queries.post_queries import (
    query_materials as query_materials_impl,
    query_posts as query_posts_impl,
)
from server_modules.queries.read_model_queries import (
    query_countries,
    query_country_cards,
    query_daily_metrics,
    query_product_kpis,
    query_product_rollups,
    query_summary,
)
from server_modules.reelfarm_utils import (
    reelfarm_dashboard_automation_condition,
    reelfarm_expected_automation_condition,
)
from server_modules.time_windows import business_material_day_window


def post_datetime_bound(value, end=False):
    return post_datetime_bound_impl(value, end, business_material_day_window=business_material_day_window)


def common_where(query, date_column="post.published_at", include_post_dates=True):
    return common_where_impl(
        query,
        date_column,
        include_post_dates,
        placeholder=db_placeholder(),
        data_source_channel_code=data_source_channel_code,
        business_material_day_window=business_material_day_window,
    )


def hydrate_museon_images_for_rows(conn, row_data_list):
    from server import hydrate_museon_images_for_rows as hydrate

    return hydrate(conn, row_data_list)


def query_accounts(query):
    return query_reelfarm_accounts_impl(
        query,
        data_source_channel_code=data_source_channel_code,
        query_value=query_value,
        query_days_window=query_days_window,
        post_datetime_bound=post_datetime_bound,
        db_placeholder=db_placeholder,
        common_where=common_where,
        reelfarm_dashboard_automation_condition=reelfarm_dashboard_automation_condition,
        reelfarm_expected_automation_condition=reelfarm_expected_automation_condition,
        using_postgres=using_postgres,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        relational_base_from=relational_base_from,
        row_dict=row_dict,
        normalize_reelfarm_account_row=normalize_reelfarm_account_row,
    )


def query_posts(query, top_metric=""):
    return query_posts_impl(
        query,
        top_metric=top_metric,
        query_limit_offset=query_limit_offset,
        common_where=common_where,
        db_placeholder=db_placeholder,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        relational_base_from=relational_base_from,
        detailed_select=detailed_select,
        row_dict=row_dict,
        query_value=query_value,
        data_source_channel_code=data_source_channel_code,
        hydrate_museon_images_for_rows=hydrate_museon_images_for_rows,
        detailed_row=detailed_row,
        pagination_payload=pagination_payload,
    )


def query_materials(query):
    return query_materials_impl(
        query,
        query_limit_offset=query_limit_offset,
        common_where=common_where,
        db_placeholder=db_placeholder,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        relational_base_from=relational_base_from,
        detailed_select=detailed_select,
        detailed_row=detailed_row,
        pagination_payload=pagination_payload,
        row_dict=row_dict,
    )


def data_query_payload(query):
    return data_query_payload_impl(
        query,
        query_value=query_value,
        compact_filters=compact_filters,
        query_filters=query_filters,
        query_summary=query_summary,
        query_product_kpis=query_product_kpis,
        query_product_rollups=query_product_rollups,
        query_country_cards=query_country_cards,
        query_countries=query_countries,
        query_accounts=query_accounts,
        query_posts=query_posts,
        query_materials=query_materials,
        query_daily_metrics=query_daily_metrics,
    )
