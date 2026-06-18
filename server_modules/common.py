import json
import re
import uuid
from datetime import datetime, timezone


def generate_id():
    return uuid.uuid4().hex[:9]


def stable_id(namespace, *parts):
    value = "|".join(str(part or "").strip() for part in parts)
    return uuid.uuid5(uuid.NAMESPACE_URL, f"deca-growth:{namespace}:{value}").hex


def slug_part(value):
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", str(value or "")).strip()
    if not cleaned:
        return "Item"
    return "".join(part[:1].upper() + part[1:] for part in cleaned.split())


def code_from_name(value):
    cleaned = re.sub(r"[^a-zA-Z0-9 ]+", " ", str(value or "")).strip()
    if not cleaned:
        return "APP"

    alias = re.sub(r"\s+", "", cleaned).lower()
    if alias in {"delust", "dl"}:
        return "DL"

    compact = re.sub(r"\s+", "", cleaned)
    if len(compact) <= 4:
        return compact.upper()

    initials = "".join(part[:1] for part in cleaned.split())
    return (initials or compact[:4]).upper()


def normalize_username(value):
    return re.sub(r"[^a-z0-9_.]+", "", str(value or "").strip().lower().lstrip("@"))


def db_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def int_or_none(value):
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def utc_snapshot_date(value=None):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def parse_json_list(value):
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def readable_utc_datetime(value):
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""

    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return raw_value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y/%m/%d %H:%M UTC")
