from server_modules.common import code_from_name


DEFAULT_PARTY_A_PRODUCT_CODES = ("DB", "DM", "DL", "DU")
PARTY_B_OWNER_MARKERS = {"乙方", "party_b", "vendor", "external"}


COUNTRY_CODES = {
    "United States": "US",
    "United Kingdom": "UK",
    "Japan": "JP",
    "Germany": "GE",
    "Brazil": "BR",
    "India": "IN",
    "China": "CN",
    "France": "FR",
    "Italy": "IT",
    "Canada": "CA",
    "Australia": "AU",
    "South Korea": "KR",
}


def _clean_text(value):
    return str(value or "").strip()


def _flag_enabled(product, keys, default=True):
    for key in keys:
        if key not in product:
            continue
        value = product.get(key)
        if isinstance(value, bool):
            return value
        text = _clean_text(value).lower()
        if text in {"1", "true", "yes", "y", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "n", "off", "disabled"}:
            return False
    return default


def product_code_for(product):
    if not isinstance(product, dict):
        return ""
    return str(product.get("reelFarmCode") or code_from_name(product.get("name"))).upper()


def country_code_for(country):
    if not isinstance(country, dict):
        return ""
    return str(
        country.get("reelFarmCode")
        or COUNTRY_CODES.get(country.get("name"), "")
        or code_from_name(country.get("name"))
    ).upper()


def configured_product_codes(products):
    product_codes = []
    seen = set()
    for product in products if isinstance(products, list) else []:
        product_code = product_code_for(product)
        if product_code and product_code not in seen:
            seen.add(product_code)
            product_codes.append(product_code)
    return product_codes


def product_owner_type(product):
    if not isinstance(product, dict):
        return ""
    return _clean_text(product.get("folder") or product.get("owner_type") or product.get("ownerType"))


def is_party_b_product(product):
    owner_type = product_owner_type(product).lower()
    return owner_type in PARTY_B_OWNER_MARKERS or product_owner_type(product) == "乙方"


def is_party_a_product(product):
    return isinstance(product, dict) and not is_party_b_product(product)


def feishu_enabled(product):
    return _flag_enabled(
        product,
        ("enabledInFeishu", "enabled_in_feishu", "feishuEnabled", "includeInFeishu", "include_in_feishu"),
        default=is_party_a_product(product),
    )


def growth_enabled(product):
    return _flag_enabled(
        product,
        ("enabledInGrowth", "enabled_in_growth", "growthEnabled", "includeInGrowth", "include_in_growth"),
        default=is_party_a_product(product),
    )


def automation_coverage_enabled(product):
    return _flag_enabled(
        product,
        (
            "enabledInAutomationCoverage",
            "enabled_in_automation_coverage",
            "automationCoverageEnabled",
            "includeInAutomationCoverage",
        ),
        default=is_party_a_product(product),
    )


def party_a_products(products):
    return [product for product in products if is_party_a_product(product)] if isinstance(products, list) else []


def feishu_report_products(products):
    return [product for product in party_a_products(products) if feishu_enabled(product)]


def growth_products(products):
    return [product for product in party_a_products(products) if growth_enabled(product)]


def automation_coverage_products(products):
    return [product for product in party_a_products(products) if automation_coverage_enabled(product)]


def growth_product_codes(products):
    codes = configured_product_codes(growth_products(products))
    return codes or list(DEFAULT_PARTY_A_PRODUCT_CODES)


def feishu_product_codes(products):
    return configured_product_codes(feishu_report_products(products))


def automation_coverage_product_codes(products):
    return configured_product_codes(automation_coverage_products(products))


def configured_product_name_map(products):
    names = {}
    for product in products if isinstance(products, list) else []:
        product_code = product_code_for(product)
        if product_code:
            names[product_code] = str(product.get("name") or product_code)
    return names


def product_registry(products):
    records = []
    seen = set()
    for index, product in enumerate(products if isinstance(products, list) else []):
        if not isinstance(product, dict):
            continue
        product_code = product_code_for(product)
        if not product_code or product_code in seen:
            continue
        seen.add(product_code)
        owner_type = product_owner_type(product) or ("乙方" if is_party_b_product(product) else "甲方")
        records.append({
            "product_id": str(product.get("id") or ""),
            "product_code": product_code,
            "product_name": str(product.get("name") or product_code),
            "owner_type": owner_type,
            "is_party_a": is_party_a_product(product),
            "enabled_in_feishu": feishu_enabled(product),
            "enabled_in_growth": growth_enabled(product),
            "enabled_in_automation_coverage": automation_coverage_enabled(product),
            "logo_url": str(product.get("logo") or product.get("logo_url") or ""),
            "sort_order": index,
        })
    return records


def product_country_lookup(products):
    lookup = {}
    for product in products if isinstance(products, list) else []:
        if not isinstance(product, dict):
            continue
        product_id = str(product.get("id") or "")
        product_code = product_code_for(product)
        for country in product.get("countries") or []:
            if not isinstance(country, dict):
                continue
            country_id = str(country.get("id") or "")
            lookup[(product_id, country_id)] = {
                "product": {
                    "id": product_id,
                    "name": product.get("name") or "",
                    "code": product_code,
                    "folder": product.get("folder") or product.get("owner_type") or "",
                },
                "country": {
                    "id": country_id,
                    "name": country.get("name") or "",
                    "code": country_code_for(country),
                },
            }
    return lookup
