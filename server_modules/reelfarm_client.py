import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from server_modules.automation_naming import automation_prefix_candidates, automation_title_matches_prefix
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


def reelfarm_matches(prefix, automations=None, *, fetch_automations_fn, request_fn):
    clean_prefix = (prefix or "").strip()
    if not clean_prefix:
        raise ValueError("Missing automation prefix.")

    candidates = automation_prefix_candidates(clean_prefix)
    automations = list(automations) if automations is not None else fetch_automations_fn()
    matched = []
    seen_automation_keys = set()
    for automation in automations:
        title = str(automation.get("title", "") or "")
        if not any(automation_title_matches_prefix(title, candidate) for candidate in candidates):
            continue
        key = str(automation.get("automation_id") or title).strip()
        if key in seen_automation_keys:
            continue
        seen_automation_keys.add(key)
        matched.append(automation)

    accounts_by_id = {}
    try:
        accounts_payload = request_fn("/tiktok/accounts")
        for account in list_payload(accounts_payload, "accounts"):
            account_id = account.get("tiktok_account_id")
            if account_id:
                accounts_by_id[account_id] = account
    except RuntimeError:
        accounts_by_id = {}

    def build_card(automation):
        automation_id = automation.get("automation_id")
        details = automation
        needs_details = (
            not automation.get("tiktok_account_id")
            or reelfarm_post_as_draft_value(automation) is None
        )
        if automation_id and needs_details:
            try:
                details = request_fn(f"/automations/{quote(str(automation_id), safe='')}")
            except RuntimeError:
                details = automation

        tiktok_account_id = details.get("tiktok_account_id") or automation.get("tiktok_account_id")
        account = accounts_by_id.get(tiktok_account_id, {}) if tiktok_account_id else {}

        def fetch_videos():
            if not automation_id:
                return {"videos": [], "total": 0}
            try:
                return request_fn(
                    "/videos",
                    {"automation_id": automation_id, "video_type": "slideshow", "limit": 50},
                )
            except RuntimeError as error:
                return {"videos": [], "total": 0, "error": str(error)}

        def fetch_posts():
            if not tiktok_account_id:
                return {"posts": [], "statistics": {}}
            try:
                return request_fn(
                    "/tiktok/posts",
                    {
                        "tiktok_account_id": tiktok_account_id,
                        "timeframe": "all",
                        "sort": "recent",
                        "limit": 50,
                    },
                )
            except RuntimeError as error:
                return {"posts": [], "statistics": {}, "error": str(error)}

        with ThreadPoolExecutor(max_workers=2) as inner_executor:
            videos_future = inner_executor.submit(fetch_videos)
            posts_future = inner_executor.submit(fetch_posts)
            videos_payload = videos_future.result()
            posts_payload = posts_future.result()

        posts = [compact_post(post) for post in list_payload(posts_payload, "posts")]
        posted_video_ids = {
            str(post.get("video_id"))
            for post in posts
            if post.get("video_id") and (post.get("post_id") or post.get("published_at"))
        }
        posted_videos = [
            video
            for video in list_payload(videos_payload, "videos")
            if str(video.get("video_id") or video.get("id")) in posted_video_ids
        ]
        videos = [compact_video(video) for video in posted_videos[:50]]
        automation_posted_video_ids = {str(video.get("video_id")) for video in videos if video.get("video_id")}
        posts = [
            post
            for post in posts
            if str(post.get("video_id")) in automation_posted_video_ids
        ]

        return {
            "automation": compact_automation(details),
            "account": compact_account(account),
            "videos": videos,
            "video_total": len(videos),
            "posts": posts,
            "post_statistics": posts_payload.get("statistics", {})
            if isinstance(posts_payload, dict)
            else {},
            "errors": {
                "videos": videos_payload.get("error")
                if isinstance(videos_payload, dict)
                else None,
                "posts": posts_payload.get("error")
                if isinstance(posts_payload, dict)
                else None,
            },
        }

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(matched)))) as executor:
        cards = list(executor.map(build_card, matched))

    return {"prefix": clean_prefix, "matched_prefixes": candidates, "count": len(cards), "cards": cards}


def reelfarm_creator_count(result):
    cards = result.get("cards", []) if isinstance(result, dict) else []
    creator_keys = set()
    for card in cards:
        if not isinstance(card, dict):
            continue

        account = card.get("account") if isinstance(card.get("account"), dict) else {}
        automation = card.get("automation") if isinstance(card.get("automation"), dict) else {}
        creator_key = str(
            account.get("tiktok_account_id")
            or automation.get("tiktok_account_id")
            or account.get("account_username")
            or account.get("username")
            or account.get("account_name")
            or automation.get("automation_id")
            or automation.get("title")
            or ""
        ).strip()
        if creator_key:
            creator_keys.add(creator_key)

    return len(creator_keys)


def reelfarm_material_count(result):
    cards = result.get("cards", []) if isinstance(result, dict) else []
    return sum(
        len(card.get("videos", []) or [])
        for card in cards
        if isinstance(card, dict)
    )
