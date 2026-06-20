from server_modules.api_keys import (
    create_external_api_key_from_state,
    external_api_key_authorized_from_state,
    load_external_api_keys_from_state,
    list_external_api_keys_from_state,
    revoke_external_api_key_from_state,
    save_external_api_keys_to_state,
)
from server_modules.app_runtime import (
    AI_API_KEY,
    EXTERNAL_API_KEYS_KEY,
    load_app_value,
    save_app_value,
)
from server_modules.common import generate_id


def load_keys():
    return load_external_api_keys_from_state(load_app_value, EXTERNAL_API_KEYS_KEY)


def save_keys(keys):
    save_external_api_keys_to_state(save_app_value, EXTERNAL_API_KEYS_KEY, keys)


def create(name, permissions=None):
    return create_external_api_key_from_state(
        name,
        permissions,
        load_value_fn=load_app_value,
        save_value_fn=save_app_value,
        state_key=EXTERNAL_API_KEYS_KEY,
        id_factory=generate_id,
    )


def revoke(key_id):
    return revoke_external_api_key_from_state(
        key_id,
        load_value_fn=load_app_value,
        save_value_fn=save_app_value,
        state_key=EXTERNAL_API_KEYS_KEY,
    )


def list_keys():
    return list_external_api_keys_from_state(load_app_value, EXTERNAL_API_KEYS_KEY)


def authorized(token, permission):
    return external_api_key_authorized_from_state(
        token,
        permission,
        ai_api_key=AI_API_KEY,
        load_value_fn=load_app_value,
        state_key=EXTERNAL_API_KEYS_KEY,
    )
