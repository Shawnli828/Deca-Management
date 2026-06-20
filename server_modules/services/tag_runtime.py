from server_modules.account_issues import (
    account_issues_payload as account_issues_payload_impl,
    add_account_issue as add_account_issue_impl,
    delete_account_issue as delete_account_issue_impl,
)
from server_modules.app_runtime import connect_db, db_placeholder, init_relational_schema
from server_modules.db_core import upsert_row as upsert_row_impl
from server_modules.reelfarm_lifecycle import active_tiktok_automation_account_ids as active_tiktok_automation_account_ids_impl
from server_modules.tags import (
    account_tags_payload as account_tags_payload_impl,
    add_account_tag as add_account_tag_impl,
    clean_tag,
    create_product_tag as create_product_tag_impl,
    delete_account_tag as delete_account_tag_impl,
    delete_product_tag as delete_product_tag_impl,
    product_tags_payload as product_tags_payload_impl,
)


def upsert_row(conn, table, values, conflict_cols, update_cols=None):
    upsert_row_impl(conn, table, values, conflict_cols, db_placeholder(), update_cols)


def active_tiktok_automation_account_ids(conn, account_ids):
    return active_tiktok_automation_account_ids_impl(conn, account_ids, placeholder=db_placeholder())


def account_tags_payload(account_ids):
    return account_tags_payload_impl(
        account_ids,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def account_issues_payload(account_ids):
    return account_issues_payload_impl(
        account_ids,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
        active_tiktok_automation_account_ids=active_tiktok_automation_account_ids,
    )


def add_account_issue(account_id, issue):
    return add_account_issue_impl(
        account_id,
        issue,
        clean_issue=clean_tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        upsert_row=upsert_row,
    )


def delete_account_issue(account_id, issue):
    return delete_account_issue_impl(
        account_id,
        issue,
        clean_issue=clean_tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def product_tags_payload(product_code):
    return product_tags_payload_impl(
        product_code,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def create_product_tag(product_code, tag):
    return create_product_tag_impl(
        product_code,
        tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        upsert_row=upsert_row,
        placeholder=db_placeholder(),
    )


def delete_product_tag(product_code, tag, remove_assignments=True):
    return delete_product_tag_impl(
        product_code,
        tag,
        remove_assignments=remove_assignments,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )


def add_account_tag(account_id, tag):
    return add_account_tag_impl(
        account_id,
        tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        upsert_row=upsert_row,
        placeholder=db_placeholder(),
    )


def delete_account_tag(account_id, tag):
    return delete_account_tag_impl(
        account_id,
        tag,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        placeholder=db_placeholder(),
    )
