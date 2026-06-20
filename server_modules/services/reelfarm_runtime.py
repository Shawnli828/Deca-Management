import os

from server_modules.app_runtime import make_ssl_context
from server_modules.app_runtime import REELFARM_API_KEY, delete_app_value, load_app_value, save_app_value
from server_modules.queries.read_model_queries import stored_reelfarm_country
from server_modules.reelfarm_client import (
    reelfarm_creator_count as reelfarm_creator_count_impl,
    reelfarm_fetch_automations as reelfarm_fetch_automations_impl,
    reelfarm_material_count as reelfarm_material_count_impl,
    reelfarm_matches as reelfarm_matches_impl,
    reelfarm_request as reelfarm_request_impl,
)
from server_modules.services.reelfarm_config_service import (
    reelfarm_config_payload,
    save_reelfarm_config_payload,
)
from server_modules.settings import REELFARM_BASE_URL


def api_key():
    return os.environ.get("REELFARM_API_KEY", "").strip() or load_app_value(REELFARM_API_KEY).strip()


def config_payload():
    return reelfarm_config_payload(reelfarm_api_key=api_key, base_url=REELFARM_BASE_URL)


def save_config_payload(raw_api_key):
    return save_reelfarm_config_payload(
        raw_api_key,
        save_app_value=save_app_value,
        delete_app_value=delete_app_value,
        state_key=REELFARM_API_KEY,
        base_url=REELFARM_BASE_URL,
    )


def request(path, query=None):
    return reelfarm_request_impl(
        path,
        query,
        api_key=api_key(),
        base_url=REELFARM_BASE_URL,
        make_ssl_context=make_ssl_context,
    )


def fetch_automations():
    return reelfarm_fetch_automations_impl(request_fn=request)


def matches(prefix):
    return reelfarm_matches_impl(
        prefix,
        fetch_automations_fn=fetch_automations,
        request_fn=request,
    )


def matches_from_automations(prefix, automations):
    return reelfarm_matches_impl(
        prefix,
        automations=automations,
        fetch_automations_fn=fetch_automations,
        request_fn=request,
    )


def creator_count(result):
    return reelfarm_creator_count_impl(result)


def material_count(result):
    return reelfarm_material_count_impl(result)


def stored_country(product_code, country_code):
    return stored_reelfarm_country(product_code, country_code)
