import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api_contract_checks import configure_test_env, seed_contract_database  # noqa: E402


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value, label):
    if not value:
        raise AssertionError(label)


def first_tab_group(card):
    elements = ((card or {}).get("body") or {}).get("elements") or []
    for element in elements:
        if element.get("tag") == "tab_group":
            return element
    raise AssertionError("card should include a tab_group")


def text_blocks(elements):
    blocks = []
    for element in elements or []:
        text = element.get("text") or {}
        content = text.get("content") or element.get("content")
        if content:
            blocks.append(str(content))
    return blocks


def main():
    configure_test_env()

    from server_modules import app_runtime
    from server_modules.domain.feishu_card import bar, build_daily_report_card
    from server_modules.external_clients import feishu_signed_card_payload
    from server_modules.services.daily_feishu_runtime import report_payload
    from server_modules.services.feishu_card_adapter import daily_report_card_data

    with tempfile.TemporaryDirectory() as tmpdir:
        app_runtime.DB_PATH = Path(tmpdir) / "feishu-card.sqlite3"
        app_runtime.reset_schema_init_cache()
        seed_contract_database(app_runtime)
        app_runtime.save_data([
            {
                "id": "product-demi",
                "name": "Demi",
                "reelFarmCode": "DM",
                "folder": "甲方",
                "countries": [
                    {"id": "country-germany", "name": "Germany", "reelFarmCode": "GE", "concepts": []},
                ],
            }
        ])

        report = report_payload("2026-06-15")
        card_data = daily_report_card_data(report)
        card = build_daily_report_card(card_data)

    totals = report.get("totals") or {}
    products = report.get("products") or []
    card_products = card_data.get("products") or []
    assert_equal(card_data.get("bizDate"), "2026-06-15", "card data report date")
    assert_equal(card_data.get("global", {}).get("totalPlays"), totals.get("total_views"), "global total views")
    assert_equal(card_data.get("global", {}).get("rfPlays"), totals.get("reelfarm_views"), "global RF views")
    assert_equal(card_data.get("global", {}).get("rfPublished"), totals.get("reelfarm_published_automations"), "global RF published")
    assert_equal(len(card_products), len(products), "card product count")
    assert_equal(card_products[0].get("name"), products[0].get("product_name"), "card product name")
    assert_equal(card_products[0].get("totalPlays"), products[0].get("total_views"), "product total views")
    assert_equal(card_products[0].get("countries", [])[0].get("rfAvg"), 1234, "country RF avg")
    assert_equal(card_products[0].get("countries", [])[0].get("flag"), "🇩🇪", "country flag")

    assert_equal(card.get("schema"), "2.0", "card schema")
    assert_equal(card.get("header", {}).get("template"), "blue", "card header template")
    tab_group = first_tab_group(card)
    tabs = tab_group.get("tabs") or []
    assert_equal(len(tabs), len(products) + 1, "card tab count")
    assert_equal(tabs[0].get("title", {}).get("content"), "总览", "overview tab title")
    assert_equal(tabs[1].get("title", {}).get("content"), products[0].get("product_name"), "product tab title")

    overview_text = "\n".join(text_blocks(tabs[0].get("elements")))
    product_text = "\n".join(text_blocks(tabs[1].get("elements")))
    assert_true("产品线总播放量" in overview_text, "overview includes play chart")
    assert_true("██████████████" in overview_text, "overview includes filled character bar")
    assert_true("国家 RF 均播" in product_text, "product tab includes country avg")

    signed_payload = feishu_signed_card_payload(card, "secret")
    assert_equal(signed_payload.get("msg_type"), "interactive", "signed payload type")
    assert_true(signed_payload.get("timestamp"), "signed payload timestamp")
    assert_true(signed_payload.get("sign"), "signed payload sign")
    assert_equal(bar(50, 100, width=10), "█████░░░░░", "bar proportion")

    print("feishu card fixture checks passed")


if __name__ == "__main__":
    main()
