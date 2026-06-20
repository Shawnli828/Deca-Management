import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def configure_test_env():
    for key in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "POSTGRES_URL_NON_POOLING"):
        os.environ.pop(key, None)


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value, label):
    if not value:
        raise AssertionError(label)


def row_dict(row):
    return dict(row) if row else {}


def fixture_data(cards):
    return [
        {
            "id": "product-demi",
            "name": "Demi",
            "reelFarmCode": "DM",
            "folder": "甲方",
            "countries": [
                {
                    "id": "country-ge",
                    "name": "Germany",
                    "reelFarmCode": "GE",
                    "reelFarmSyncedAt": "2026-06-20T00:00:00+00:00",
                    "concepts": [{"group": "SeedTopic", "name": "SeedFormat"}],
                    "reelFarmResult": {"cards": cards},
                }
            ],
        }
    ]


def active_card():
    return {
        "account": {
            "tiktok_account_id": "rf-account-1",
            "account_username": "demi_ge",
            "account_name": "Demi GE",
            "account_image": "https://example.test/avatar.png",
            "status": "active",
        },
        "automation": {
            "automation_id": "rf-auto-1",
            "title": "GE-DM-Hooks-FormatA",
            "status": "active",
            "schedule": ["09:00", "18:00"],
            "tiktok_post_settings": {"auto_post": True},
            "created_at": "2026-06-16T00:00:00+00:00",
        },
        "videos": [
            {
                "video_id": "rf-video-1",
                "video_type": "slideshow",
                "hook": "first hook",
                "prompt": "first prompt",
                "slideshow_images": ["a.png", "b.png"],
                "status": "Finished",
                "created_at": "2026-06-17T00:00:00+00:00",
                "finished_at": "2026-06-17T00:01:00+00:00",
            },
            {
                "video_id": "rf-video-2",
                "video_type": "slideshow",
                "hook": "second hook",
                "prompt": "second prompt",
                "slideshow_images": ["c.png"],
                "status": "Finished",
                "created_at": "2026-06-18T00:00:00+00:00",
                "finished_at": "2026-06-18T00:01:00+00:00",
            },
        ],
        "posts": [
            {
                "post_id": "rf-post-1",
                "video_id": "rf-video-1",
                "status": "published",
                "title": "first post",
                "published_at": "2026-06-17T02:00:00+00:00",
                "published_at_readable": "2026/06/17 02:00 UTC",
                "view_count": 10,
                "like_count": 1,
                "comment_count": 2,
                "share_count": 3,
                "bookmark_count": 4,
            },
            {
                "post_id": "rf-post-2",
                "video_id": "rf-video-2",
                "status": "published",
                "title": "second post",
                "published_at": "2026-06-18T02:00:00+00:00",
                "published_at_readable": "2026/06/18 02:00 UTC",
                "view_count": 20,
                "like_count": 5,
                "comment_count": 6,
                "share_count": 7,
                "bookmark_count": 8,
            },
        ],
    }


def main():
    configure_test_env()

    from server_modules import app_runtime
    from server_modules.services.reelfarm_projection_runtime import project_products_to_relational

    with tempfile.TemporaryDirectory() as tmpdir:
        app_runtime.DB_PATH = Path(tmpdir) / "projection.sqlite3"
        app_runtime.reset_schema_init_cache()

        result = project_products_to_relational(fixture_data([active_card()]))
        assert_true(result.get("ok") is True, "projection should succeed")
        tables = result.get("tables") or {}
        assert_equal(tables.get("accounts"), 1, "account count")
        assert_equal(tables.get("automations"), 1, "automation count")
        assert_equal(tables.get("materials"), 2, "material count")
        assert_equal(tables.get("posts"), 2, "post count")
        assert_equal(tables.get("post_daily_snapshots"), 2, "snapshot count")

        with app_runtime.connect_db() as conn:
            app_runtime.init_relational_schema(conn)
            account = row_dict(conn.execute("SELECT username, status FROM accounts LIMIT 1").fetchone())
            automation = row_dict(
                conn.execute(
                    "SELECT name, post_mode, publish_method, sync_status FROM automations LIMIT 1"
                ).fetchone()
            )
            material_total = row_dict(conn.execute("SELECT SUM(slide_count) AS count FROM materials").fetchone())
            post_total = row_dict(conn.execute("SELECT SUM(view_count) AS views FROM posts").fetchone())
            issue = row_dict(conn.execute("SELECT issue, source FROM account_issues LIMIT 1").fetchone())
            concept = row_dict(conn.execute("SELECT name FROM concepts WHERE name = 'Hooks'").fetchone())

        assert_equal(account.get("username"), "demi_ge", "account username")
        assert_equal(account.get("status"), "active", "account status")
        assert_equal(automation.get("name"), "GE-DM-Hooks-FormatA", "automation name")
        assert_equal(automation.get("post_mode"), "DIRECT_POST", "automation post mode")
        assert_equal(automation.get("publish_method"), "api", "automation publish method")
        assert_equal(automation.get("sync_status"), "present", "automation sync status")
        assert_equal(material_total.get("count"), 3, "material slide count")
        assert_equal(post_total.get("views"), 30, "post view total")
        assert_equal(issue.get("issue"), "0播警告", "zero-play issue")
        assert_equal(issue.get("source"), "auto", "zero-play issue source")
        assert_equal(concept.get("name"), "Hooks", "automation concept parsing")

        project_products_to_relational(fixture_data([]))
        with app_runtime.connect_db() as conn:
            app_runtime.init_relational_schema(conn)
            deleted = row_dict(conn.execute("SELECT sync_status FROM automations LIMIT 1").fetchone())
            issue_count = row_dict(conn.execute("SELECT COUNT(*) AS count FROM account_issues").fetchone())

        assert_equal(deleted.get("sync_status"), "deleted", "missing automation cleanup")
        assert_equal(issue_count.get("count"), 0, "zero-play cleanup for deleted automation")

    print("reelfarm projection fixture checks passed")


if __name__ == "__main__":
    main()
