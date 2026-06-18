import json
import re


REELFARM_POST_AS_DRAFT_KEYS = {
    "post_as_draft",
    "postAsDraft",
    "post_as_draft_enabled",
    "postAsDraftEnabled",
}


def bool_from_api(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if text in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return False


def nested_value(payload, keys):
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload:
            return payload.get(key)
    for value in payload.values():
        if isinstance(value, dict):
            found = nested_value(value, keys)
            if found is not None:
                return found
    return None


def reelfarm_tiktok_post_settings(automation):
    if not isinstance(automation, dict):
        return {}
    settings = automation.get("tiktok_post_settings")
    if isinstance(settings, dict):
        return settings
    settings = automation.get("tiktokPostSettings")
    if isinstance(settings, dict):
        return settings
    return {}


def reelfarm_post_mode(automation):
    settings = reelfarm_tiktok_post_settings(automation)
    post_mode = str(settings.get("post_mode") or settings.get("postMode") or "").strip().upper()
    if post_mode:
        return post_mode
    auto_post = settings.get("auto_post", settings.get("autoPost"))
    if auto_post is not None:
        return "DIRECT_POST" if bool_from_api(auto_post) else "MEDIA_UPLOAD"
    return ""


def reelfarm_post_as_draft_value(automation):
    post_mode = reelfarm_post_mode(automation)
    if post_mode:
        return post_mode == "MEDIA_UPLOAD"

    exact = nested_value(automation, REELFARM_POST_AS_DRAFT_KEYS)
    if exact is not None:
        return exact

    def walk(payload):
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized = re.sub(r"[^a-z0-9]+", "", str(key).lower())
                if "draft" in normalized and ("post" in normalized or "publish" in normalized):
                    return value
                found = walk(value)
                if found is not None:
                    return found
        elif isinstance(payload, list):
            for value in payload:
                found = walk(value)
                if found is not None:
                    return found
        return None

    return walk(automation)


def reelfarm_publish_method(automation):
    post_as_draft = reelfarm_post_as_draft_value(automation)
    return "manual" if bool_from_api(post_as_draft) else "api"


def reelfarm_schedule_slot_count(schedule_value):
    if isinstance(schedule_value, str):
        raw = schedule_value.strip()
        if not raw:
            return 1
        try:
            schedule_value = json.loads(raw)
        except json.JSONDecodeError:
            return 1

    if isinstance(schedule_value, list):
        return max(len([item for item in schedule_value if item not in (None, "")]), 1)

    if isinstance(schedule_value, dict):
        for key in ("schedule", "schedules", "times", "cron", "crons"):
            value = schedule_value.get(key)
            if value not in (None, "", [], {}):
                return reelfarm_schedule_slot_count(value)
        return 1

    return 1
