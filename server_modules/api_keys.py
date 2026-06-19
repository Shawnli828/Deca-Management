import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone


def hash_api_key(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def parse_external_api_keys(value):
    if not value:
        return []

    try:
        keys = json.loads(value)
    except json.JSONDecodeError:
        return []

    return keys if isinstance(keys, list) else []


def serialize_external_api_keys(keys):
    return keys if isinstance(keys, list) else []


def public_external_api_key(key_record):
    return {
        "id": key_record.get("id"),
        "name": key_record.get("name"),
        "prefix": key_record.get("prefix"),
        "permissions": key_record.get("permissions", []),
        "active": bool(key_record.get("active")),
        "created_at": key_record.get("created_at"),
        "revoked_at": key_record.get("revoked_at"),
    }


def create_external_api_key_record(name, permissions=None, id_factory=None):
    now = datetime.now(timezone.utc).isoformat()
    raw_key = f"deca_{secrets.token_urlsafe(32)}"
    key_record = {
        "id": id_factory() if id_factory else secrets.token_hex(5),
        "name": (name or "External AI").strip() or "External AI",
        "prefix": raw_key[:14],
        "key_hash": hash_api_key(raw_key),
        "permissions": permissions or ["materials:read"],
        "active": True,
        "created_at": now,
        "revoked_at": None,
    }
    return raw_key, key_record


def revoke_external_api_key_record(keys, key_id):
    now = datetime.now(timezone.utc).isoformat()
    updated_record = None
    for key_record in keys:
        if str(key_record.get("id")) == str(key_id):
            key_record["active"] = False
            key_record["revoked_at"] = now
            updated_record = key_record
            break

    if updated_record is None:
        raise ValueError("API key not found.")

    return updated_record


def list_public_external_api_keys(keys):
    return [public_external_api_key(key_record) for key_record in keys]


def external_api_key_authorized(token, permission, ai_api_key, key_records):
    if not token:
        return False
    if ai_api_key and hmac.compare_digest(token, ai_api_key):
        return True

    token_hash = hash_api_key(token)
    for key_record in key_records:
        if not key_record.get("active"):
            continue
        if permission not in (key_record.get("permissions") or []):
            continue
        if hmac.compare_digest(str(key_record.get("key_hash", "")), token_hash):
            return True

    return False


def load_external_api_keys_from_state(load_value_fn, state_key):
    return parse_external_api_keys(load_value_fn(state_key))


def save_external_api_keys_to_state(save_value_fn, state_key, keys):
    save_value_fn(state_key, serialize_external_api_keys(keys))


def create_external_api_key_from_state(
    name,
    permissions,
    *,
    load_value_fn,
    save_value_fn,
    state_key,
    id_factory,
):
    raw_key, key_record = create_external_api_key_record(name, permissions, id_factory)
    keys = load_external_api_keys_from_state(load_value_fn, state_key)
    keys.append(key_record)
    save_external_api_keys_to_state(save_value_fn, state_key, keys)
    return {"key": raw_key, "record": public_external_api_key(key_record)}


def revoke_external_api_key_from_state(
    key_id,
    *,
    load_value_fn,
    save_value_fn,
    state_key,
):
    keys = load_external_api_keys_from_state(load_value_fn, state_key)
    updated_record = revoke_external_api_key_record(keys, key_id)
    save_external_api_keys_to_state(save_value_fn, state_key, keys)
    return public_external_api_key(updated_record)


def list_external_api_keys_from_state(load_value_fn, state_key):
    return list_public_external_api_keys(load_external_api_keys_from_state(load_value_fn, state_key))


def external_api_key_authorized_from_state(
    token,
    permission,
    *,
    ai_api_key,
    load_value_fn,
    state_key,
):
    return external_api_key_authorized(
        token,
        permission,
        ai_api_key,
        load_external_api_keys_from_state(load_value_fn, state_key),
    )
