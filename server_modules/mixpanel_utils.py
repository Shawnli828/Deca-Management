import os
from datetime import datetime


MIXPANEL_SERVICE_ACCOUNT_USERNAME = os.environ.get("MIXPANEL_SERVICE_ACCOUNT_USERNAME", "").strip()
MIXPANEL_SERVICE_ACCOUNT_SECRET = os.environ.get("MIXPANEL_SERVICE_ACCOUNT_SECRET", "").strip()
MIXPANEL_PROJECT_ID = os.environ.get("MIXPANEL_PROJECT_ID", "").strip()
MIXPANEL_REGION = os.environ.get("MIXPANEL_REGION", "standard").strip().lower()
MIXPANEL_DOWNLOAD_EVENT = os.environ.get("MIXPANEL_DOWNLOAD_EVENT", "Download").strip()
MIXPANEL_ONBOARDING_EVENT = os.environ.get("MIXPANEL_ONBOARDING_EVENT", "Onboarding Step Viewed").strip()


def collect_numeric_values(value):
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        values = []
        for child in value.values():
            values.extend(collect_numeric_values(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(collect_numeric_values(child))
        return values
    return []


def mixpanel_segmentation_unique_from_payload(payload, event_name):
    if not isinstance(payload, dict):
        return 0
    data = payload.get("data")
    if isinstance(data, dict):
        values = data.get("values")
        if isinstance(values, dict):
            candidate = values.get(event_name)
            if candidate is None and len(values) == 1:
                candidate = next(iter(values.values()))
            return int(round(sum(collect_numeric_values(candidate))))
    results = payload.get("results")
    if isinstance(results, dict):
        return int(round(sum(collect_numeric_values(results))))
    return 0


def product_mixpanel_config(product_code):
    code = str(product_code or "").strip().upper()
    project_id = (
        os.environ.get(f"MIXPANEL_PROJECT_ID_{code}", "").strip()
        or os.environ.get(f"{code}_MIXPANEL_PROJECT_ID", "").strip()
    )
    username = (
        os.environ.get(f"MIXPANEL_SERVICE_ACCOUNT_USERNAME_{code}", "").strip()
        or os.environ.get(f"{code}_MIXPANEL_SERVICE_ACCOUNT_USERNAME", "").strip()
    )
    secret = (
        os.environ.get(f"MIXPANEL_SERVICE_ACCOUNT_SECRET_{code}", "").strip()
        or os.environ.get(f"{code}_MIXPANEL_SERVICE_ACCOUNT_SECRET", "").strip()
    )
    region = (
        os.environ.get(f"MIXPANEL_REGION_{code}", "").strip().lower()
        or os.environ.get(f"{code}_MIXPANEL_REGION", "").strip().lower()
    )
    has_product_credentials = bool(project_id or username or secret)
    if has_product_credentials:
        return {
            "project_id": project_id,
            "username": username,
            "secret": secret,
            "region": region or MIXPANEL_REGION,
            "scope": "product",
        }
    return {
        "project_id": MIXPANEL_PROJECT_ID,
        "username": MIXPANEL_SERVICE_ACCOUNT_USERNAME,
        "secret": MIXPANEL_SERVICE_ACCOUNT_SECRET,
        "region": region or MIXPANEL_REGION,
        "scope": "global",
    }


def product_mixpanel_project_id(product_code):
    return product_mixpanel_config(product_code)["project_id"]


def product_mixpanel_event_name(product_code, event_kind):
    code = str(product_code or "").strip().upper()
    kind = str(event_kind or "").strip().upper()
    default_value = MIXPANEL_ONBOARDING_EVENT if kind == "ONBOARDING" else MIXPANEL_DOWNLOAD_EVENT
    return (
        os.environ.get(f"MIXPANEL_{kind}_EVENT_{code}", "").strip()
        or os.environ.get(f"{code}_MIXPANEL_{kind}_EVENT", "").strip()
        or os.environ.get(f"MIXPANEL_EVENT_{kind}_{code}", "").strip()
        or default_value
    )


def mixpanel_query_base_url(region=None):
    region = (region or MIXPANEL_REGION).strip().lower()
    if region == "eu":
        return "https://eu.mixpanel.com/api/query"
    if region in {"in", "india"}:
        return "https://in.mixpanel.com/api/query"
    return "https://mixpanel.com/api/query"


def mixpanel_export_base_url(region=None):
    region = (region or MIXPANEL_REGION).strip().lower()
    if region == "eu":
        return "https://data-eu.mixpanel.com/api/2.0/export"
    if region in {"in", "india"}:
        return "https://data-in.mixpanel.com/api/2.0/export"
    return "https://data.mixpanel.com/api/2.0/export"


def mixpanel_distinct_id(event, properties):
    if not isinstance(properties, dict):
        properties = {}
    if not isinstance(event, dict):
        event = {}
    for key in ("distinct_id", "$distinct_id", "user_id", "$user_id", "$device_id", "device_id"):
        value = properties.get(key)
        if value:
            return str(value)
    value = event.get("distinct_id")
    return str(value) if value else ""


def mixpanel_source_day_span(source_date_from, source_date_to):
    try:
        start = datetime.strptime(source_date_from, "%Y-%m-%d").date()
        end = datetime.strptime(source_date_to, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return 1
    return max(1, (end - start).days + 1)
