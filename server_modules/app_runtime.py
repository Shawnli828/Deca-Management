import json

from server_modules.app_context import AppContext
from server_modules.auth_utils import (
    make_auth_token as make_signed_auth_token,
    valid_auth_token as signed_auth_token_valid,
)
from server_modules.common import generate_id
from server_modules.db_core import (
    connect_db as connect_db_impl,
    database_snapshot_payload as database_snapshot_payload_impl,
    db_placeholder as db_placeholder_impl,
    delete_app_value as delete_app_value_impl,
    init_app_state_db,
    load_app_value as load_app_value_impl,
    make_ssl_context as make_ssl_context_impl,
    save_app_value as save_app_value_impl,
    using_postgres as using_postgres_impl,
)
from server_modules.schema import (
    init_relational_schema as init_relational_schema_impl,
    relational_table_counts as relational_table_counts_impl,
)
from server_modules.settings import (
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
    AI_API_KEY,
    BASE_DIR,
    DATABASE_URL,
    DB_PATH,
    EXTERNAL_API_KEYS_KEY,
    PUBLISH_CHECK_STATE_KEY,
    REELFARM_API_KEY,
    SEED_DATA_PATH,
    SESSION_COOKIE,
    SESSION_SECRET,
    SESSION_TTL_SECONDS,
    STATE_KEY,
)
from server_modules.state_helpers import (
    clean_publish_check_state,
    data_source_channel_code as data_source_channel_code_impl,
    default_data as default_data_impl,
    initial_data as initial_data_impl,
    parse_publish_check_state,
    strip_reelfarm_state as strip_reelfarm_state_impl,
)


APP_CONTEXT = AppContext(
    database_url=lambda: DATABASE_URL,
    db_path=lambda: DB_PATH,
    using_postgres_impl=using_postgres_impl,
    db_placeholder_impl=db_placeholder_impl,
    connect_db_impl=connect_db_impl,
    init_relational_schema_impl=init_relational_schema_impl,
)


def using_postgres():
    return APP_CONTEXT.using_postgres()


def db_placeholder():
    return APP_CONTEXT.db_placeholder()


def make_ssl_context():
    return make_ssl_context_impl()


def default_data():
    return default_data_impl(generate_id)


def initial_data():
    return initial_data_impl(SEED_DATA_PATH, generate_id)


def connect_db():
    return APP_CONTEXT.connect_db()


def init_relational_schema(conn):
    APP_CONTEXT.init_relational_schema(conn)


def reset_schema_init_cache():
    APP_CONTEXT.reset_schema_init_cache()


def init_db():
    init_app_state_db(connect_db, init_relational_schema, db_placeholder(), STATE_KEY, initial_data, save_data)


def save_app_value(key, value, conn=None):
    save_app_value_impl(key, value, connect_db, db_placeholder(), conn)


def load_app_value(key):
    return load_app_value_impl(key, init_db, connect_db, db_placeholder())


def delete_app_value(key):
    delete_app_value_impl(key, init_db, connect_db, db_placeholder())


def strip_reelfarm_state(value):
    return strip_reelfarm_state_impl(value)


def save_data(data, conn=None):
    payload = json.dumps(strip_reelfarm_state(data), ensure_ascii=False, separators=(",", ":"))
    save_app_value(STATE_KEY, payload, conn)


def load_data():
    init_db()
    value = load_app_value(STATE_KEY)

    if not value:
        data = default_data()
        save_data(data)
        return data

    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        data = default_data()
        save_data(data)
        return data

    if not isinstance(data, list):
        return default_data()

    clean_data = strip_reelfarm_state(data)
    if clean_data != data:
        save_data(clean_data)
    return clean_data


def load_publish_check_state():
    return parse_publish_check_state(load_app_value(PUBLISH_CHECK_STATE_KEY))


def save_publish_check_state(state):
    clean = clean_publish_check_state(state, generate_id)
    save_app_value(PUBLISH_CHECK_STATE_KEY, clean)
    return clean


def data_source_channel_code(source):
    return data_source_channel_code_impl(source)


def make_auth_token(username):
    return make_signed_auth_token(username, SESSION_SECRET, SESSION_TTL_SECONDS)


def valid_auth_token(token):
    return signed_auth_token_valid(token, ADMIN_USERNAME, SESSION_SECRET)


def database_snapshot(relational_table_counts_fn=relational_table_counts_impl):
    return database_snapshot_payload_impl(
        init_db_fn=init_db,
        connect_db_fn=connect_db,
        placeholder=db_placeholder(),
        state_key=STATE_KEY,
        db_path=DB_PATH,
        database_backend="postgres" if using_postgres() else "sqlite",
        relational_table_counts_fn=relational_table_counts_fn,
        load_data_fn=load_data,
    )
