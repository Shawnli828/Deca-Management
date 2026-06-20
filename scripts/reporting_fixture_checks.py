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


def main():
    configure_test_env()

    from server_modules import app_runtime
    from server_modules.repositories import daily_feishu_repository, growth_repository
    from server_modules.services import growth_runtime, museon_runtime
    from server_modules.sync_result import normalized_sync_result
    from server_modules.time_windows import business_material_day_window

    with tempfile.TemporaryDirectory() as tmpdir:
        app_runtime.DB_PATH = Path(tmpdir) / "reporting.sqlite3"
        app_runtime.reset_schema_init_cache()
        seed_contract_database(app_runtime)

        material_window = business_material_day_window("2026-06-15")
        rf_views = growth_repository.product_channel_views_for_window(
            "DM",
            "TIKTOK",
            material_window["utc_start"],
            material_window["utc_end"],
        )
        assert_equal(rf_views["posts"], 1, "growth repository post count")
        assert_equal(rf_views["views"], 1234, "growth repository views")

        business_daily = growth_runtime.product_business_material_daily_stats(
            "DM",
            material_window["utc_start"],
            material_window["utc_end"],
        )
        assert_equal(business_daily["2026-06-15"]["reelfarm_materials"], 1, "business material materials")
        assert_equal(business_daily["2026-06-15"]["reelfarm_views"], 1234, "business material views")

        growth_daily = growth_runtime.product_business_growth_daily_stats(
            "DM",
            [{"report_date": "2026-06-15"}],
        )
        assert_equal(growth_daily["2026-06-15"]["reelfarm_posts"], 1, "growth delta posts")
        assert_equal(growth_daily["2026-06-15"]["reelfarm_views"], 1234, "growth delta views")

        country_avg = daily_feishu_repository.product_reelfarm_country_avg_views(
            "DM",
            material_window["utc_start"],
            material_window["utc_end"],
        )
        assert_equal(country_avg[0]["country_code"], "GE", "Feishu country avg country")
        assert_equal(country_avg[0]["reelfarm_avg_views"], 1234.0, "Feishu country avg views")

        original_clone_campaign = museon_runtime.clone_campaign
        original_all_posts = museon_runtime.all_posts
        original_posts = museon_runtime.posts
        try:
            museon_runtime.clone_campaign = lambda product_code, country_code: {
                "id": "campaign-1",
                "name": f"{country_code}-{product_code}-Clone",
                "status": "active",
            }
            museon_runtime.all_posts = lambda campaign_id, date_from="", date_to="", max_pages=40: [
                {
                    "id": "museon-post-1",
                    "content_id": "museon-content-1",
                    "account": {"id": "creator-1", "username": "clone_ge", "display_name": "Clone GE"},
                    "published_at": "2026-06-15T04:00:00+00:00",
                    "title": "Clone post 1",
                    "metrics": {"views": 30, "likes": 3, "comments": 2, "shares": 1, "saves": 4},
                    "images": ["https://example.test/1.png"],
                },
                {
                    "id": "museon-post-2",
                    "content_id": "museon-content-2",
                    "account": {"id": "creator-1", "username": "clone_ge", "display_name": "Clone GE"},
                    "published_at": "2026-06-15T05:00:00+00:00",
                    "title": "Clone post 2",
                    "metrics": {"views": 70, "likes": 7, "comments": 5, "shares": 2, "saves": 6},
                    "images": ["https://example.test/2.png"],
                },
            ]

            clone_accounts = museon_runtime.query_clone_accounts(
                {
                    "product_code": ["DM"],
                    "country_code": ["GE"],
                    "date_from": ["2026-06-15"],
                    "date_to": ["2026-06-15"],
                }
            )
            assert_equal(len(clone_accounts), 1, "Museon account grouping")
            assert_equal(clone_accounts[0]["post_count"], 2, "Museon post count")
            assert_equal(clone_accounts[0]["total_views"], 100, "Museon grouped views")

            museon_runtime.posts = lambda campaign_id, date_from="", date_to="", username="", page=1, page_size=100, sort="": (
                museon_runtime.all_posts(campaign_id, date_from, date_to),
                2,
            )
            clone_post_rows, clone_pagination = museon_runtime.query_clone_account_posts(
                {
                    "product_code": ["DM"],
                    "country_code": ["GE"],
                    "account_id": ["museon:DM:GE:clone_ge"],
                    "date_from": ["2026-06-15"],
                    "date_to": ["2026-06-15"],
                }
            )
            assert_equal(len(clone_post_rows), 2, "Museon account post rows")
            assert_equal(clone_post_rows[0]["metrics"]["view_count"], 30, "Museon post metrics")
            assert_equal(clone_pagination["total"], 2, "Museon pagination total")
        finally:
            museon_runtime.clone_campaign = original_clone_campaign
            museon_runtime.all_posts = original_all_posts
            museon_runtime.posts = original_posts

        sync_result = normalized_sync_result(
            "daily_all",
            {
                "ok": True,
                "stages": {
                    "reelfarm": {"records": [{"id": 1}, {"id": 2}]},
                    "museon_clone": {"records_count": 3},
                },
            },
            product_code="dm",
            country_code="ge",
        )
        assert_equal(sync_result["records_count"], 5, "nested sync record count")
        assert_equal(sync_result["product_code"], "DM", "sync product code normalization")
        assert_equal(sync_result["country_code"], "GE", "sync country code normalization")
        assert_true(sync_result["synced_at"], "sync result synced_at")

    print("reporting fixture checks passed")


if __name__ == "__main__":
    main()
