import json
import os
import re
import urllib.error
import urllib.request
import uuid
from typing import Any


class GeelarkServiceError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def geelark_api_token(env=None) -> str:
    source = env or os.environ
    return source.get("GEELARK_API_TOKEN", "").strip() or source.get("GEELARK_API_KEY", "").strip()


def geelark_post(path: str, payload: dict[str, Any], *, env=None, timeout=30) -> dict[str, Any]:
    token = geelark_api_token(env)
    if not token:
        raise GeelarkServiceError(400, "GEELARK_API_TOKEN is not configured")

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://openapi.geelark.com{path}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "traceId": str(uuid.uuid4()),
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", "ignore")
        raise GeelarkServiceError(exc.code, f"GeeLark API error: {body_text[:500]}") from exc
    except Exception as exc:
        raise GeelarkServiceError(502, f"GeeLark request failed: {exc}") from exc


def geelark_phone_items(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    container = payload.get("data")
    total = None
    items: list[dict[str, Any]] = []
    if isinstance(container, dict):
        total = container.get("total") or container.get("count")
        for key in ("items", "list", "records", "data"):
            value = container.get(key)
            if isinstance(value, list):
                items = [item for item in value if isinstance(item, dict)]
                break
    elif isinstance(container, list):
        items = [item for item in container if isinstance(item, dict)]
    return items, total if isinstance(total, int) else None


def geelark_group_name(phone: dict[str, Any]) -> str:
    group = phone.get("group") if isinstance(phone.get("group"), dict) else {}
    return str(group.get("name") or phone.get("groupName") or "")


def geelark_group_matches(group_name: str, product_code: str, country_code: str) -> bool:
    tokens = [token for token in re.split(r"[-_\\s]+", group_name.upper()) if token]
    return product_code.upper() in tokens and country_code.upper() in tokens


def sanitize_geelark_phone(phone: dict[str, Any]) -> dict[str, Any]:
    equipment = phone.get("equipmentInfo") if isinstance(phone.get("equipmentInfo"), dict) else {}
    tags = phone.get("tags") if isinstance(phone.get("tags"), list) else []
    return {
        "id": str(phone.get("id") or phone.get("phoneId") or ""),
        "serialName": phone.get("serialName") or "",
        "serialNo": phone.get("serialNo") or "",
        "groupName": geelark_group_name(phone),
        "countryName": equipment.get("countryName") or phone.get("countryName") or "",
        "timeZone": equipment.get("timeZone") or phone.get("timeZone") or "",
        "deviceModel": equipment.get("deviceModel") or "",
        "netType": equipment.get("netType") or "",
        "status": phone.get("status"),
        "rpaStatus": phone.get("rpaStatus"),
        "tags": [str(tag.get("name")) for tag in tags if isinstance(tag, dict) and tag.get("name")],
    }


def load_geelark_phones(*, post=geelark_post) -> tuple[list[dict[str, Any]], int | None]:
    all_phones: list[dict[str, Any]] = []
    total: int | None = None
    page_size = 100
    for page in range(1, 20):
        response = post("/open/v1/phone/list", {"page": page, "pageSize": page_size})
        if response.get("code") not in (0, "0", None):
            raise GeelarkServiceError(502, response.get("msg") or response.get("message") or "GeeLark API failed")
        items, response_total = geelark_phone_items(response)
        if response_total is not None:
            total = response_total
        all_phones.extend(items)
        if len(items) < page_size:
            break
    return all_phones, total


def geelark_payload_for_pair(all_phones: list[dict[str, Any]], product_code: str, country_code: str, total: int | None = None) -> dict[str, Any]:
    clean_product = product_code.strip().upper()
    clean_country = country_code.strip().upper()
    matched = [
        sanitize_geelark_phone(phone)
        for phone in all_phones
        if geelark_group_matches(geelark_group_name(phone), clean_product, clean_country)
    ]

    groups: dict[str, dict[str, Any]] = {}
    for phone in matched:
        group_name = phone["groupName"] or f"{clean_country}-{clean_product}"
        group = groups.setdefault(
            group_name,
            {
                "id": group_name,
                "name": group_name,
                "productCode": clean_product,
                "countryCode": clean_country,
                "countryName": phone.get("countryName") or "",
                "phones": [],
            },
        )
        group["phones"].append(phone)
        if phone.get("countryName"):
            group["countryName"] = phone["countryName"]

    ordered_groups = sorted(
        groups.values(),
        key=lambda item: [int(part) if part.isdigit() else part for part in re.split(r"(\\d+)", item["name"])],
    )

    return {
        "ok": True,
        "source": "geelark",
        "filters": {"product_code": clean_product, "country_code": clean_country},
        "total_loaded": total if total is not None else len(all_phones),
        "phone_count": len(matched),
        "group_count": len(ordered_groups),
        "groups": ordered_groups,
    }


def geelark_phone_payload(product_code: str, country_code: str) -> dict[str, Any]:
    all_phones, total = load_geelark_phones()
    return geelark_payload_for_pair(all_phones, product_code, country_code, total)


def geelark_phone_map_payload(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    all_phones, total = load_geelark_phones()
    items = [
        geelark_payload_for_pair(all_phones, product_code, country_code, total)
        for product_code, country_code in pairs
    ]
    return {
        "ok": True,
        "source": "geelark",
        "pairs": [item["filters"] for item in items],
        "total_loaded": total if total is not None else len(all_phones),
        "phone_count": sum(int(item.get("phone_count") or 0) for item in items),
        "group_count": sum(int(item.get("group_count") or 0) for item in items),
        "items": items,
    }
