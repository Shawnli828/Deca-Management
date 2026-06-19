import re

from server_modules.common import code_from_name, slug_part
from server_modules.product_config import COUNTRY_CODES


def _country_code(country):
    return (
        country.get("reelFarmCode")
        or COUNTRY_CODES.get(country.get("name"))
        or code_from_name(country.get("name"))
    ).upper()


def _product_code(product):
    return (product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()


def build_automation_prefix(product, country, concept):
    country_code = _country_code(country)
    product_code = _product_code(product)
    topic = slug_part(concept.get("group") or "Topic")
    format_name = slug_part(concept.get("name") or "Format")
    return f"{country_code}-{product_code}-{topic}-{format_name}"


def build_country_automation_prefix(product, country):
    return f"{_country_code(country)}-{_product_code(product)}"


def automation_prefix_candidates(prefix):
    clean = str(prefix or "").strip()
    if not clean:
        return []

    candidates = [clean]
    parts = [part for part in re.split(r"[-_]+", clean) if part]
    if len(parts) >= 2:
        reversed_first_pair = "-".join([parts[1], parts[0], *parts[2:]])
        candidates.append(reversed_first_pair)

    deduped = []
    seen = set()
    for candidate in candidates:
        key = candidate.upper()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def automation_title_matches_prefix(title, prefix):
    clean_title = str(title or "").strip().upper()
    clean_prefix = str(prefix or "").strip().upper()
    if not clean_title or not clean_prefix:
        return False
    return (
        clean_title == clean_prefix
        or clean_title.startswith(f"{clean_prefix}-")
        or clean_title.startswith(f"{clean_prefix}_")
    )


def prefixes_equivalent(left, right):
    left_values = {candidate.upper() for candidate in automation_prefix_candidates(left)}
    right_value = str(right or "").strip().upper()
    return bool(right_value and right_value in left_values)


def parse_concept_format_from_automation(title, country_code, product_code):
    clean_title = str(title or "").strip()
    prefixes = [
        f"{country_code}-{product_code}",
        f"{product_code}-{country_code}",
    ]
    matched_prefix = ""
    for prefix in prefixes:
        if automation_title_matches_prefix(clean_title, prefix):
            matched_prefix = prefix.upper()
            break
    if not matched_prefix:
        return "", ""

    remainder = clean_title[len(matched_prefix):].lstrip("-_")
    parts = [part for part in re.split(r"[-_]+", remainder) if part]
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    if len(parts) < 2:
        return "", ""

    return parts[0], "-".join(parts[1:])
