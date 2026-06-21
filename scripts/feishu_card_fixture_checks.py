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
    from server_modules.services.daily_feishu_service import DailyFeishuReportService
    from server_modules.services.feishu_card_adapter import daily_report_card_data

    trend_service = DailyFeishuReportService(
        env={},
        webhook_url="",
        webhook_secret="",
        llm_api_base="",
        llm_model="",
        fallback_llm_models=[],
        report_timezone_name="Asia/Shanghai",
        make_ssl_context=lambda: None,
        configured_product_codes=lambda: [],
        configured_product_name_map=lambda: {},
        business_material_report_payload=lambda _query: {
            "rows": [
                {"report_date": "2026-06-19", "total_views": 100, "downloads": 10},
                {"report_date": "2026-06-20", "total_views": 20, "downloads": 2},
                {"report_date": "2026-06-21", "total_views": 30, "downloads": 3},
            ]
        },
        daily_reelfarm_account_alerts=lambda *_args, **_kwargs: {},
        product_reelfarm_country_avg_views=lambda *_args, **_kwargs: [],
        sync_status_payload=lambda: {},
        sync_readiness_payload=lambda *_args, **_kwargs: {},
    )
    daily_trend = trend_service.report_trend("2026-06-21", ["DB"], days=3)
    assert_equal([row["date"] for row in daily_trend["products"]["DB"]], ["2026-06-20", "2026-06-21"], "trend should start at configured business date")
    assert_equal(daily_trend["products"]["DB"][0]["view"], 20, "trend first included day daily view")
    assert_equal(daily_trend["products"]["DB"][1]["view"], 30, "trend second day should not accumulate")
    assert_equal(daily_trend["overview"][1]["download"], 3, "overview download should stay daily")

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
    assert_equal(card_products[0].get("totalPosts"), products[0].get("total_posts"), "product total posts")
    assert_equal(card_products[0].get("totalPlays"), products[0].get("total_views"), "product total views")
    assert_equal(card_products[0].get("countries", [])[0].get("rfAvg"), 1234, "country RF avg")
    assert_equal(card_products[0].get("countries", [])[0].get("flag"), "🇩🇪", "country flag")
    assert_equal(len(card_data.get("trend") or []), 0, "card trend before configured start should be empty")
    trend_groups = card_data.get("trendGroups") or []
    assert_equal([group.get("label") for group in trend_groups], ["总览", "Demi"], "card trend groups")
    assert_equal(len(trend_groups[1].get("trend") or []), 0, "product trend before configured start should be empty")

    assert_equal(card.get("schema"), "2.0", "card schema")
    assert_equal(card.get("header", {}).get("template"), "blue", "card header template")
    elements = ((card or {}).get("body") or {}).get("elements") or []
    assert_true(elements, "card should include body elements")
    assert_true(all(element.get("tag") != "tab_group" for element in elements), "webhook-safe card should not use tab_group")

    card_text = "\n".join(text_blocks(elements))
    assert_true("各 App 当日数据" in card_text, "card includes daily app table")
    assert_true(products[0].get("product_name") in card_text, "card includes product row")
    assert_true("|Demi|1/1|" in card_text, "daily table post column uses RF publish coverage")
    assert_true("RF Avg View" in card_text, "daily table includes RF avg view")
    assert_true("View / Download 日趋势" in card_text, "card includes daily trend section")
    assert_true("|日期|View|Download|" in card_text, "trend table includes daily view and download")

    signed_payload = feishu_signed_card_payload(card, "secret")
    assert_equal(signed_payload.get("msg_type"), "interactive", "signed payload type")
    assert_true(signed_payload.get("timestamp"), "signed payload timestamp")
    assert_true(signed_payload.get("sign"), "signed payload sign")
    assert_equal(bar(50, 100, width=10), "█████░░░░░", "bar proportion")

    print("feishu card fixture checks passed")


if __name__ == "__main__":
    main()
