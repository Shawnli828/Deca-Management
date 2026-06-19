import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from server_modules.museon_utils import (
    museon_list_payload,
    museon_pagination_total,
    normalize_image_entries,
)


_CAMPAIGN_CACHE = {"loaded_at": 0, "campaigns": []}


def museon_request(path, params=None, *, api_key, base_url, user_agent, make_ssl_context):
    if not api_key:
        raise RuntimeError("MUSEON_API_KEY is not configured.")
    clean_path = "/" + str(path or "").lstrip("/")
    query = urlencode(params or {}, doseq=True)
    url = f"{base_url}{clean_path}" + (f"?{query}" if query else "")
    request = Request(url, headers={
        "X-API-KEY": api_key,
        "Accept": "application/json",
        "User-Agent": user_agent,
    })
    try:
        with urlopen(request, timeout=20, context=make_ssl_context()) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Museon returned HTTP {exc.code}: {detail[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Museon API: {exc.reason}") from exc

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError("Museon returned a non-JSON response.") from exc
    if isinstance(payload, dict) and payload.get("error"):
        error = payload.get("error") or {}
        raise RuntimeError(error.get("message") or error.get("code") or "Museon API error")
    return payload


def museon_campaigns(*, request_fn, workspace_id, force=False):
    now = time.time()
    if not force and _CAMPAIGN_CACHE["campaigns"] and now - _CAMPAIGN_CACHE["loaded_at"] < 300:
        return _CAMPAIGN_CACHE["campaigns"]

    campaigns = []
    page = 1
    while page <= 20:
        payload = request_fn(
            "/campaigns",
            {"workspace_id": workspace_id, "page": page, "page_size": 100},
        )
        items = museon_list_payload(payload)
        campaigns.extend([item for item in items if isinstance(item, dict)])
        pagination = payload.get("pagination") if isinstance(payload, dict) else {}
        total = int((pagination or {}).get("total") or 0)
        if not items or (total and len(campaigns) >= total):
            break
        page += 1

    _CAMPAIGN_CACHE["campaigns"] = campaigns
    _CAMPAIGN_CACHE["loaded_at"] = now
    return campaigns


def museon_clone_campaign(product_code, country_code, *, campaigns_fn):
    product_code = str(product_code or "").strip().upper()
    country_code = str(country_code or "").strip().upper()
    if not product_code or not country_code:
        return None
    exact_names = {
        f"{country_code}-{product_code}-CLONE",
        f"{product_code}-{country_code}-CLONE",
        f"{country_code}_{product_code}_CLONE",
        f"{product_code}_{country_code}_CLONE",
    }
    fallback = None
    for campaign in campaigns_fn():
        name = str(campaign.get("name") or campaign.get("title") or "").strip()
        upper_name = name.upper()
        tokens = {token for token in re.split(r"[^A-Z0-9]+", upper_name) if token}
        if upper_name in exact_names:
            return campaign
        if "CLONE" in tokens and product_code in tokens and country_code in tokens:
            fallback = fallback or campaign
    return fallback


def museon_clone_campaigns_for_product(
    product_code,
    country_code="",
    *,
    products,
    country_codes,
    code_from_name,
    clone_campaign_fn,
):
    product_code = str(product_code or "").strip().upper()
    country_code = str(country_code or "").strip().upper()
    if not product_code:
        return []
    if country_code:
        campaign = clone_campaign_fn(product_code, country_code)
        return [{"country_code": country_code, "campaign": campaign}] if campaign else []

    contexts = []
    for product in products if isinstance(products, list) else []:
        code = str(product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()
        if code != product_code:
            continue
        for country in product.get("countries") or []:
            ccode = str(
                country.get("reelFarmCode")
                or country_codes.get(country.get("name"), "")
                or code_from_name(country.get("name"))
            ).upper()
            campaign = clone_campaign_fn(product_code, ccode)
            if campaign:
                contexts.append({"country_code": ccode, "campaign": campaign})
        break
    return contexts


def museon_posts(
    campaign_id,
    date_from="",
    date_to="",
    username="",
    page=1,
    page_size=100,
    sort="",
    *,
    request_fn,
    post_datetime_bound,
):
    params = {"page": page, "page_size": page_size}
    if sort:
        params["sort"] = sort
    if username:
        params["username"] = username
    if date_from:
        params["published_after"] = post_datetime_bound(date_from)
    if date_to:
        params["published_before"] = post_datetime_bound(date_to, end=True)
    payload = request_fn(f"/campaigns/{quote(str(campaign_id), safe='')}/posts", params)
    return museon_list_payload(payload), museon_pagination_total(payload)


def museon_all_posts(campaign_id, date_from="", date_to="", max_pages=40, *, posts_fn):
    posts = []
    page = 1
    total = 0
    while True:
        if max_pages and page > max_pages:
            break
        items, total = posts_fn(campaign_id, date_from, date_to, page=page, page_size=100)
        posts.extend([item for item in items if isinstance(item, dict)])
        if not items or (total and len(posts) >= total):
            break
        page += 1
    return posts


def museon_content_download_images(content_id, *, request_fn):
    if not content_id:
        return []
    try:
        payload = request_fn(f"/content/{quote(str(content_id), safe='')}/download-urls")
    except RuntimeError:
        return []
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return []
    values = []
    for key in ("download_urls", "image_urls", "media_urls"):
        if isinstance(data.get(key), list):
            values.extend(data.get(key) or [])
    if data.get("thumbnail_url"):
        values.append(data.get("thumbnail_url"))
    return normalize_image_entries(values)
