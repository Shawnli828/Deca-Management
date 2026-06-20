from fastapi import APIRouter, HTTPException, Request

from server_modules.services.geelark_service import (
    GeelarkServiceError,
    geelark_phone_map_payload,
    geelark_phone_payload,
)

from .shared import require_dashboard_auth


router = APIRouter()


def parse_geelark_pairs(pairs: str) -> list[tuple[str, str]]:
    parsed_pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw_pair in pairs.split(","):
        parts = [part.strip().upper() for part in raw_pair.replace("-", ":").split(":") if part.strip()]
        if len(parts) != 2:
            continue
        product_code, country_code = parts
        key = f"{product_code}:{country_code}"
        if key in seen:
            continue
        seen.add(key)
        parsed_pairs.append((product_code, country_code))
    return parsed_pairs


@router.get("/api/geelark/phones")
def get_geelark_phones(request: Request, product_code: str = "DB", country_code: str = "GE"):
    require_dashboard_auth(request)
    clean_product = product_code.strip().upper()
    clean_country = country_code.strip().upper()
    if not clean_product or not clean_country:
        raise HTTPException(status_code=400, detail="product_code and country_code are required")

    try:
        return geelark_phone_payload(clean_product, clean_country)
    except GeelarkServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@router.get("/api/geelark/phones-map")
def get_geelark_phones_map(request: Request, pairs: str = ""):
    require_dashboard_auth(request)
    parsed_pairs = parse_geelark_pairs(pairs)
    if not parsed_pairs:
        raise HTTPException(status_code=400, detail="pairs is required, for example DB:GE,DB:US")
    if len(parsed_pairs) > 120:
        raise HTTPException(status_code=400, detail="Too many GeeLark pairs requested")

    try:
        return geelark_phone_map_payload(parsed_pairs)
    except GeelarkServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error
