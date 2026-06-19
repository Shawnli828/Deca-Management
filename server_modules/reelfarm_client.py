import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from server_modules.common import readable_utc_datetime, stable_id
from server_modules.reelfarm_utils import (
    reelfarm_post_as_draft_value,
    reelfarm_post_mode,
    reelfarm_publish_method,
)


def reelfarm_request(path, query=None, *, api_key, base_url, make_ssl_context):
    if not api_key:
        raise RuntimeError("ReelFarm API key is not configured.")

    url = f"{base_url}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"

    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ManagementTable/1.0",
        },
    )

    try:
        with urlopen(request, timeout=25, context=make_ssl_context()) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ReelFarm API error {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach ReelFarm API: {error.reason}") from error


def list_payload(payload, key):
    value = payload.get(key) if isinstance(payload, dict) else None
    return value if isinstance(value, list) else []


def reelfarm_fetch_automations(*, request_fn):
    automations_payload = request_fn("/automations")
    return list_payload(automations_payload, "automations")


def automation_title_product_code_matches(title, product_code):
    code = str(product_code or "").strip().upper()
    if not code:
        return False
    parts = [part.upper() for part in re.split(r"[-_]+", str(title or "")) if part]
    return code in parts[:3]


def reelfarm_product_automation_ids(automations, product_code):
    ids = set()
    for automation in automations or []:
        if not isinstance(automation, dict):
            continue
        title = automation.get("title") or ""
        if not automation_title_product_code_matches(title, product_code):
            continue
        automation_id = str(
            automation.get("automation_id") or stable_id("automation_source", title)
        ).strip()
        if automation_id:
            ids.add(automation_id)
    return ids


def video_identifier(video):
    for key in ("video_id", "id", "uuid"):
        value = video.get(key)
        if value is not None:
            return str(value)
    return ""


def compact_automation(automation):
    return {
        "automation_id": automation.get("automation_id"),
        "title": automation.get("title"),
        "status": automation.get("status"),
        "tiktok_account_id": automation.get("tiktok_account_id"),
        "schedule": automation.get("schedule", []),
        "post_mode": reelfarm_post_mode(automation),
        "post_as_draft": reelfarm_post_as_draft_value(automation),
        "publish_method": reelfarm_publish_method(automation),
        "created_at": automation.get("created_at"),
    }


def compact_account(account):
    return {
        "tiktok_account_id": account.get("tiktok_account_id"),
        "account_name": account.get("account_name"),
        "account_username": account.get("account_username"),
        "account_image": account.get("account_image"),
    }


def compact_video(video):
    images = video.get("slideshow_images")
    if not isinstance(images, list):
        images = []

    prompt = video.get("prompt") or ""
    hook_match = re.search(
        r"(?:first slide text saying|first slide text says|first slide.*?saying)\s+['\"]([^'\"]+)['\"]",
        prompt,
        re.IGNORECASE,
    )

    return {
        "video_id": video.get("video_id") or video.get("id"),
        "created_at": video.get("created_at"),
        "finished_at": video.get("finished_at"),
        "status": video.get("status"),
        "finished": video.get("finished"),
        "failed": video.get("failed"),
        "video_type": video.get("video_type"),
        "video_url": video.get("video_url"),
        "slideshow_images": images,
        "slide_count": len(images),
        "hook": hook_match.group(1) if hook_match else "",
        "prompt": prompt,
    }


def compact_post(post):
    published_at = post.get("published_at")
    return {
        "post_id": post.get("post_id"),
        "video_id": post.get("video_id"),
        "status": post.get("status") or post.get("post_status"),
        "title": post.get("title"),
        "account_username": post.get("account_username"),
        "published_at": published_at,
        "published_at_meta": published_at,
        "published_at_readable": readable_utc_datetime(published_at),
        "view_count": post.get("view_count"),
        "like_count": post.get("like_count"),
        "comment_count": post.get("comment_count"),
        "share_count": post.get("share_count"),
        "bookmark_count": post.get("bookmark_count"),
    }
