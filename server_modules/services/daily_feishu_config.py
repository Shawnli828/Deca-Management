from server_modules.services.feishu_template_variables import parse_product_names


DEFAULT_FEISHU_OVERVIEW_TEMPLATE_ID = "AAqNdTzlwzkaC"
DEFAULT_FEISHU_PRODUCT_TEMPLATE_ID = "AAqNBsXlJdHqX"
DEFAULT_FEISHU_OVERVIEW_TEMPLATE_VERSION = "1.0.2"
DEFAULT_FEISHU_PRODUCT_TEMPLATE_VERSION = "1.0.0"
DEFAULT_DAILY_REPORT_CHAT_ID = "oc_8a24e41ee7f2872b17724d830d818d84"
FEISHU_TREND_START_DATE = "2026-06-17"


def daily_feishu_template_config(env):
    env = env or {}
    overview_template_id = (
        env.get("FEISHU_OVERVIEW_TEMPLATE_ID", "").strip()
        or DEFAULT_FEISHU_OVERVIEW_TEMPLATE_ID
    )
    overview_template_version = (
        env.get("FEISHU_OVERVIEW_TEMPLATE_VERSION", "").strip()
        or DEFAULT_FEISHU_OVERVIEW_TEMPLATE_VERSION
    )
    if (
        overview_template_id == DEFAULT_FEISHU_OVERVIEW_TEMPLATE_ID
        and overview_template_version == "1.0.0"
    ):
        overview_template_version = DEFAULT_FEISHU_OVERVIEW_TEMPLATE_VERSION

    return {
        "app_id": env.get("FEISHU_APP_ID", "").strip(),
        "app_secret": env.get("FEISHU_APP_SECRET", "").strip(),
        "chat_id": (
            env.get("FEISHU_DAILY_REPORT_CHAT_ID", "").strip()
            or DEFAULT_DAILY_REPORT_CHAT_ID
            or env.get("FEISHU_CHAT_ID", "").strip()
        ),
        "overview_template_id": overview_template_id,
        "overview_template_version": overview_template_version,
        "product_template_id": (
            env.get("FEISHU_PRODUCT_TEMPLATE_ID", "").strip()
            or DEFAULT_FEISHU_PRODUCT_TEMPLATE_ID
        ),
        "product_template_version": (
            env.get("FEISHU_PRODUCT_TEMPLATE_VERSION", "").strip()
            or DEFAULT_FEISHU_PRODUCT_TEMPLATE_VERSION
        ),
        "product_names": parse_product_names(env.get("FEISHU_TEMPLATE_PRODUCT_NAMES", "")),
    }
