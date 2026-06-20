def reelfarm_config_payload(*, reelfarm_api_key, base_url):
    return {
        "configured": bool(reelfarm_api_key()),
        "base_url": base_url,
    }


def save_reelfarm_config_payload(api_key, *, save_app_value, delete_app_value, state_key, base_url):
    clean_api_key = str(api_key or "").strip()
    if clean_api_key:
        save_app_value(state_key, clean_api_key)
    else:
        delete_app_value(state_key)

    return {
        "ok": True,
        "configured": bool(clean_api_key),
        "base_url": base_url,
    }
