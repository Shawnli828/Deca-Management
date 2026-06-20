from server_modules.automation_naming import parse_concept_format_from_automation
from server_modules.common import db_json, int_or_none, stable_id
from server_modules.reelfarm_utils import (
    reelfarm_automation_is_active,
    reelfarm_post_mode,
    reelfarm_publish_method,
)


def concept_format_projection(product_id, concept_name, format_name):
    concept_name = str(concept_name or "").strip()
    format_name = str(format_name or "").strip()
    if not concept_name or not format_name:
        return {"concept_id": None, "format_id": None, "concept_row": None, "format_row": None}

    concept_id = stable_id("concept", product_id, concept_name)
    format_id = stable_id("format", concept_id, format_name)
    return {
        "concept_id": concept_id,
        "format_id": format_id,
        "concept_row": {
            "id": concept_id,
            "product_id": product_id,
            "name": concept_name,
            "description": "",
        },
        "format_row": {
            "id": format_id,
            "concept_id": concept_id,
            "name": format_name,
            "description": "",
        },
    }


def configured_concept_format_projections(product_id, concepts):
    projections = []
    for concept in concepts or []:
        if not isinstance(concept, dict):
            continue
        concept_name = str(concept.get("group") or "默认 Topic").strip() or "默认 Topic"
        format_name = str(concept.get("name") or "默认 Format").strip() or "默认 Format"
        projections.append(concept_format_projection(product_id, concept_name, format_name))
    return projections


def card_projection(card, *, product_id, product_market_channel_id, product_code, market_code, synced_at):
    if not isinstance(card, dict):
        return None

    account = card.get("account") if isinstance(card.get("account"), dict) else {}
    automation = card.get("automation") if isinstance(card.get("automation"), dict) else {}
    automation_reelfarm_id = str(
        automation.get("automation_id") or stable_id("automation_source", automation.get("title"))
    )
    automation_title = str(automation.get("title") or automation_reelfarm_id)
    reelfarm_account_id = str(
        account.get("tiktok_account_id")
        or automation.get("tiktok_account_id")
        or account.get("account_username")
        or automation_reelfarm_id
    )
    account_id = stable_id("account", product_market_channel_id, reelfarm_account_id)
    automation_id = stable_id("automation", automation_reelfarm_id)
    concept_name, format_name = parse_concept_format_from_automation(
        automation_title,
        market_code,
        product_code,
    )
    concept_projection = concept_format_projection(product_id, concept_name, format_name)

    return {
        "account": account,
        "automation": automation,
        "account_id": account_id,
        "automation_id": automation_id,
        "automation_reelfarm_id": automation_reelfarm_id,
        "automation_title": automation_title,
        "reelfarm_account_id": reelfarm_account_id,
        "is_active_tiktok_automation": reelfarm_automation_is_active(automation),
        "concept_id": concept_projection["concept_id"],
        "format_id": concept_projection["format_id"],
        "concept_row": concept_projection["concept_row"],
        "format_row": concept_projection["format_row"],
        "posts_by_video": {
            str(post.get("video_id")): post
            for post in (card.get("posts") or [])
            if isinstance(post, dict)
        },
        "videos": [video for video in (card.get("videos") or []) if isinstance(video, dict)],
        "account_row": {
            "id": account_id,
            "product_market_channel_id": product_market_channel_id,
            "source": "reelfarm",
            "source_account_id": reelfarm_account_id,
            "reelfarm_account_id": reelfarm_account_id,
            "username": account.get("account_username") or account.get("account_name") or "",
            "display_name": account.get("account_name") or "",
            "avatar_url": account.get("account_image") or "",
            "status": account.get("status") or automation.get("status") or "",
        },
        "automation_row": {
            "id": automation_id,
            "product_market_channel_id": product_market_channel_id,
            "account_id": account_id,
            "source": "reelfarm",
            "source_automation_id": automation_reelfarm_id,
            "reelfarm_automation_id": automation_reelfarm_id,
            "name": automation_title,
            "status": automation.get("status") or "",
            "schedule": db_json(automation.get("schedule", [])),
            "settings_json": db_json(automation),
            "post_mode": automation.get("post_mode") or reelfarm_post_mode(automation),
            "publish_method": automation.get("publish_method") or reelfarm_publish_method(automation),
            "sync_status": "present",
            "last_seen_at": synced_at,
            "deleted_at": "",
            "created_at": automation.get("created_at") or "",
            "synced_at": synced_at,
        },
    }


def material_projection(video, *, card, product_market_channel_id, synced_at):
    if not isinstance(video, dict):
        return None
    reelfarm_video_id = str(video.get("video_id") or video.get("id") or "")
    if not reelfarm_video_id:
        return None

    material_id = stable_id("material", reelfarm_video_id)
    images = video.get("slideshow_images") if isinstance(video.get("slideshow_images"), list) else []
    return {
        "material_id": material_id,
        "reelfarm_video_id": reelfarm_video_id,
        "row": {
            "id": material_id,
            "automation_id": card["automation_id"],
            "product_market_channel_id": product_market_channel_id,
            "account_id": card["account_id"],
            "concept_id": card["concept_id"],
            "format_id": card["format_id"],
            "source": "reelfarm",
            "source_material_id": reelfarm_video_id,
            "reelfarm_video_id": reelfarm_video_id,
            "video_type": video.get("video_type") or "",
            "hook": video.get("hook") or "",
            "prompt": video.get("prompt") or "",
            "images_json": db_json(images),
            "slide_count": int_or_none(video.get("slide_count")) or len(images),
            "status": video.get("status") or "",
            "created_at": video.get("created_at") or "",
            "finished_at": video.get("finished_at") or "",
            "synced_at": synced_at,
        },
    }


def post_projection(post, *, material_id, account_id, synced_at, snapshot_date):
    if not isinstance(post, dict):
        return None

    reelfarm_post_id = str(post.get("post_id") or stable_id("post_source", material_id))
    post_id = stable_id("post", reelfarm_post_id)
    return {
        "post_id": post_id,
        "reelfarm_post_id": reelfarm_post_id,
        "post_row": {
            "id": post_id,
            "material_id": material_id,
            "account_id": account_id,
            "source": "reelfarm",
            "source_post_id": reelfarm_post_id,
            "reelfarm_post_id": reelfarm_post_id,
            "status": post.get("status") or "",
            "title": post.get("title") or "",
            "published_at": post.get("published_at") or "",
            "published_at_readable": post.get("published_at_readable") or "",
            "view_count": int_or_none(post.get("view_count")),
            "like_count": int_or_none(post.get("like_count")),
            "comment_count": int_or_none(post.get("comment_count")),
            "share_count": int_or_none(post.get("share_count")),
            "bookmark_count": int_or_none(post.get("bookmark_count")),
            "synced_at": synced_at,
        },
        "snapshot_row": {
            "id": stable_id("post_daily_snapshot", post_id, snapshot_date),
            "post_id": post_id,
            "snapshot_date": snapshot_date,
            "view_count": int_or_none(post.get("view_count")),
            "like_count": int_or_none(post.get("like_count")),
            "comment_count": int_or_none(post.get("comment_count")),
            "share_count": int_or_none(post.get("share_count")),
            "bookmark_count": int_or_none(post.get("bookmark_count")),
            "synced_at": synced_at,
        },
    }
