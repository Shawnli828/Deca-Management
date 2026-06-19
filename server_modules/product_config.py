from server_modules.common import code_from_name


COUNTRY_CODES = {
    "United States": "US",
    "United Kingdom": "UK",
    "Japan": "JP",
    "Germany": "DE",
    "Brazil": "BR",
    "India": "IN",
    "China": "CN",
    "France": "FR",
    "Italy": "IT",
    "Canada": "CA",
    "Australia": "AU",
    "South Korea": "KR",
}


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


def configured_product_name_map(products):
    names = {}
    for product in products if isinstance(products, list) else []:
        product_code = product_code_for(product)
        if product_code:
            names[product_code] = str(product.get("name") or product_code)
    return names


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
