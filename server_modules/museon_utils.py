def museon_list_payload(payload):
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        if isinstance(payload.get("items"), list):
            return payload["items"]
    return payload if isinstance(payload, list) else []


def museon_pagination_total(payload, fallback_count=0):
    if isinstance(payload, dict):
        pagination = payload.get("pagination") or payload.get("meta") or {}
        for key in ("total", "total_count", "count"):
            if isinstance(pagination, dict) and pagination.get(key) is not None:
                try:
                    return int(pagination.get(key) or 0)
                except (TypeError, ValueError):
                    pass
    return fallback_count


def museon_account_from_post(post):
    account = post.get("account") if isinstance(post.get("account"), dict) else {}
    username = account.get("username") or post.get("username") or post.get("account_username")
    return {
        "id": account.get("id") or post.get("creator_id") or post.get("account_id") or username,
        "username": username,
        "display_name": account.get("display_name") or account.get("name") or username,
        "avatar_url": account.get("avatar_url") or account.get("image_url") or account.get("profile_image_url"),
        "status": account.get("status") or post.get("status") or "active",
        "category_tags": account.get("category_tags") or [],
    }


def museon_post_metrics(post):
    metrics = post.get("metrics") if isinstance(post.get("metrics"), dict) else {}
    return {
        "view_count": int(metrics.get("views") or metrics.get("view_count") or post.get("views") or 0),
        "like_count": int(metrics.get("likes") or metrics.get("like_count") or post.get("likes") or 0),
        "comment_count": int(metrics.get("comments") or metrics.get("comment_count") or post.get("comments") or 0),
        "share_count": int(metrics.get("shares") or metrics.get("share_count") or post.get("shares") or 0),
        "bookmark_count": int(metrics.get("saves") or metrics.get("bookmark_count") or metrics.get("bookmarks") or 0),
    }


def normalize_image_entries(values):
    images = []
    for item in values or []:
        if isinstance(item, str):
            url = item
        elif isinstance(item, dict):
            url = item.get("image_url") or item.get("url") or item.get("src") or item.get("download_url")
        else:
            url = ""
        if url:
            images.append({"image_url": url})

    seen = set()
    deduped = []
    for image in images:
        url = image.get("image_url")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(image)
    return deduped


def museon_post_images(post):
    candidates = [
        post.get("slideshow_images"),
        post.get("images"),
        post.get("media_urls"),
        post.get("image_urls"),
    ]
    content = post.get("content") if isinstance(post.get("content"), dict) else {}
    candidates.extend([
        content.get("slideshow_images"),
        content.get("images"),
        content.get("media_urls"),
        content.get("image_urls"),
    ])

    images = []
    for candidate in candidates:
        if isinstance(candidate, list):
            images.extend(candidate)
    return normalize_image_entries(images)


def museon_content_id_from_material_source(value):
    text = str(value or "")
    if not text.startswith("museon:"):
        return ""
    parts = text.split(":")
    return parts[-1] if len(parts) >= 3 else ""
