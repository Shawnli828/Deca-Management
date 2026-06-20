import os

from server_modules.app_runtime import (
    connect_db,
    db_placeholder,
    init_relational_schema,
    load_data,
    load_publish_check_state,
    make_ssl_context,
    save_publish_check_state,
)
from server_modules.data_query_helpers import row_dict
from server_modules.external_clients import send_feishu_message as send_feishu_message_client
from server_modules.product_config import product_country_lookup as product_country_lookup_impl
from server_modules.reelfarm_utils import reelfarm_expected_automation_condition
from server_modules.services.publish_check_service import (
    product_country_lookup as product_country_lookup_service,
    publish_check_accounts as publish_check_accounts_service,
    run_publish_check as run_publish_check_service,
    send_publish_check_reminder as send_publish_check_reminder_service,
)


def load_state():
    return load_publish_check_state()


def save_state(state):
    return save_publish_check_state(state)


def product_country_lookup():
    return product_country_lookup_service(
        load_data=load_data,
        product_country_lookup_impl=product_country_lookup_impl,
    )


def publish_check_accounts(product_code, country_code, utc_start, utc_end):
    return publish_check_accounts_service(
        product_code,
        country_code,
        utc_start,
        utc_end,
        db_placeholder=db_placeholder,
        connect_db=connect_db,
        init_relational_schema=init_relational_schema,
        reelfarm_expected_automation_condition=reelfarm_expected_automation_condition,
        row_dict=row_dict,
    )


def run():
    return run_publish_check_service(
        load_publish_check_state=load_state,
        save_publish_check_state=save_state,
        product_country_lookup=product_country_lookup,
        publish_check_accounts=publish_check_accounts,
    )


def send_feishu_message(message):
    return send_feishu_message_client(
        message,
        os.environ.get("FEISHU_WEBHOOK_URL", "").strip(),
        os.environ.get("FEISHU_WEBHOOK_SECRET", "").strip(),
        make_ssl_context,
    )


def send_reminder():
    return send_publish_check_reminder_service(
        load_publish_check_state=load_state,
        send_feishu_message=send_feishu_message,
    )
