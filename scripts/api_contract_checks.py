import hashlib
import os
import sys
import tempfile
from pathlib import Path

from architecture_boundary_checks import assert_no_runtime_server_imports


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ADMIN_USERNAME = "contract-admin"
ADMIN_PASSWORD = "contract-password"


def configure_test_env():
    for key in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "POSTGRES_URL_NON_POOLING"):
        os.environ.pop(key, None)
    for key in ("LLM_API_KEY", "OPENAI_API_KEY"):
        os.environ.pop(key, None)
    os.environ["ADMIN_USERNAME"] = ADMIN_USERNAME
    os.environ["ADMIN_PASSWORD_HASH"] = hashlib.sha256(ADMIN_PASSWORD.encode("utf-8")).hexdigest()
    os.environ["SESSION_SECRET"] = "contract-session-secret"
    os.environ["CRON_SECRET"] = "contract-cron-secret"


def assert_status(response, expected, label):
    if response.status_code != expected:
        raise AssertionError(f"{label}: expected HTTP {expected}, got {response.status_code}: {response.text[:500]}")


def assert_true(value, label):
    if not value:
        raise AssertionError(label)


def seed_contract_database(server):
    server.init_db()
    server.save_data([
        {
            "id": "product-demi",
            "name": "Demi",
            "folder": "甲方",
            "countries": [
                {"id": "country-germany", "name": "Germany", "concepts": []},
                {"id": "country-us", "name": "United States", "concepts": []},
            ],
        }
    ])

    synced_at = "2026-06-20T00:00:00+00:00"
    with server.connect_db() as conn:
        server.init_relational_schema(conn)
        rows = [
            ("channels", {"id": "channel-tiktok", "name": "TikTok", "code": "TIKTOK"}),
            ("products", {"id": "product-demi", "name": "Demi", "code": "DM", "owner_type": "甲方", "logo_url": "", "created_at": synced_at, "updated_at": synced_at}),
            ("markets", {"id": "market-ge", "name": "Germany", "code": "GE"}),
            ("product_markets", {"id": "pm-dm-ge", "product_id": "product-demi", "market_id": "market-ge"}),
            ("product_market_channels", {"id": "pmc-dm-ge-tiktok", "product_market_id": "pm-dm-ge", "channel_id": "channel-tiktok"}),
            ("accounts", {"id": "account-dm-ge-1", "product_market_channel_id": "pmc-dm-ge-tiktok", "reelfarm_account_id": "rf-account-1", "username": "demi_ge", "display_name": "Demi GE", "avatar_url": "", "status": "active"}),
            ("automations", {"id": "automation-dm-ge-1", "product_market_channel_id": "pmc-dm-ge-tiktok", "account_id": "account-dm-ge-1", "reelfarm_automation_id": "rf-auto-1", "name": "GE-DM-topic-format", "status": "active", "schedule": "[]", "settings_json": "{}", "post_mode": "DIRECT_POST", "publish_method": "api", "sync_status": "present", "last_seen_at": synced_at, "deleted_at": "", "created_at": synced_at, "synced_at": synced_at}),
            ("materials", {"id": "material-dm-ge-1", "automation_id": "automation-dm-ge-1", "product_market_channel_id": "pmc-dm-ge-tiktok", "account_id": "account-dm-ge-1", "concept_id": None, "format_id": None, "reelfarm_video_id": "rf-video-1", "video_type": "slideshow", "hook": "contract hook", "prompt": "contract prompt", "images_json": "[]", "slide_count": 3, "status": "Finished", "created_at": "2026-06-15T00:00:00+00:00", "finished_at": "2026-06-15T00:01:00+00:00", "synced_at": synced_at}),
            ("posts", {"id": "post-dm-ge-1", "material_id": "material-dm-ge-1", "account_id": "account-dm-ge-1", "reelfarm_post_id": "rf-post-1", "status": "published", "title": "contract post", "published_at": "2026-06-15T01:00:00+00:00", "published_at_readable": "2026/06/15 01:00 UTC", "view_count": 1234, "like_count": 100, "comment_count": 10, "share_count": 5, "bookmark_count": 2, "synced_at": synced_at}),
            ("post_daily_snapshots", {"id": "snapshot-dm-ge-1", "post_id": "post-dm-ge-1", "snapshot_date": "2026-06-15", "view_count": 1234, "like_count": 100, "comment_count": 10, "share_count": 5, "bookmark_count": 2, "synced_at": synced_at}),
        ]
        for table, values in rows:
            server.upsert_row(conn, table, values, [next(iter(values.keys()))])
        conn.commit()


def main():
    configure_test_env()
    assert_no_runtime_server_imports()

    from fastapi.testclient import TestClient
    import server
    import server_modules.app_runtime as app_runtime
    from api.index import app

    with tempfile.TemporaryDirectory() as tmpdir:
        server.DB_PATH = Path(tmpdir) / "contract.sqlite3"
        app_runtime.DB_PATH = server.DB_PATH
        server.reset_schema_init_cache()
        seed_contract_database(server)

        client = TestClient(app)

        health = client.get("/api/health")
        assert_status(health, 200, "health")
        assert_true(health.json().get("database_backend") == "sqlite", "health should use sqlite test database")

        unauthenticated = client.get("/api/data")
        assert_status(unauthenticated, 401, "dashboard auth gate")

        login = client.post("/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
        assert_status(login, 200, "login")
        assert_true(login.json().get("authenticated") is True, "login should authenticate")

        data = client.get("/api/data")
        assert_status(data, 200, "data")
        products = data.json().get("data") or []
        assert_true(products and products[0].get("reelFarmCode") == "DM", "Demi should resolve to DM")
        countries = products[0].get("countries") or []
        assert_true(any(country.get("name") == "Germany" and country.get("reelFarmCode") == "GE" for country in countries), "Germany should resolve to GE")

        accounts = client.get("/api/data/query", params={
            "resource": "accounts",
            "product_code": "DM",
            "country_code": "GE",
            "date_from": "2026-06-13",
            "date_to": "2026-06-19",
        })
        assert_status(accounts, 200, "account query")
        account_rows = accounts.json().get("data") or []
        assert_true(len(account_rows) == 1, "account query should return seeded account")
        assert_true(account_rows[0].get("total_views") == 1234, "account query should return seeded views")

        posts = client.get("/api/data/query", params={
            "resource": "posts",
            "product_code": "DM",
            "country_code": "GE",
            "date_from": "2026-06-13",
            "date_to": "2026-06-19",
        })
        assert_status(posts, 200, "post query")
        post_rows = posts.json().get("data") or []
        assert_true(len(post_rows) == 1, "post query should return seeded post")
        assert_true((post_rows[0].get("metrics") or {}).get("view_count") == 1234, "post query should return seeded metrics")

        materials = client.get("/api/data/query", params={
            "resource": "materials",
            "product_code": "DM",
            "country_code": "GE",
            "date_from": "2026-06-13",
            "date_to": "2026-06-19",
        })
        assert_status(materials, 200, "material query")
        material_rows = materials.json().get("data") or []
        assert_true(len(material_rows) == 1, "material query should return seeded material")
        assert_true((material_rows[0].get("material") or {}).get("hook") == "contract hook", "material query should return seeded material fields")

        summary = client.get("/api/data/query", params={
            "resource": "summary",
            "product_code": "DM",
            "country_code": "GE",
            "date_from": "2026-06-13",
            "date_to": "2026-06-19",
        })
        assert_status(summary, 200, "summary query")
        assert_true((summary.json().get("data") or {}).get("total_views") == 1234, "summary query should return seeded views")

        countries = client.get("/api/data/query", params={"resource": "countries", "product_code": "DM", "country_code": "GE"})
        assert_status(countries, 200, "countries query")
        country_rows = countries.json().get("data") or []
        assert_true(country_rows and country_rows[0].get("total_views") == 1234, "countries query should return seeded country totals")

        product_kpis = client.get("/api/data/query", params={"resource": "product_kpis", "product_code": "DM", "country_code": "GE"})
        assert_status(product_kpis, 200, "product kpis query")
        assert_true((product_kpis.json().get("data") or {}).get("seven_day", {}).get("views") == 1234, "product kpis should include seeded seven-day views")

        daily_metrics = client.get("/api/data/query", params={
            "resource": "daily_metrics",
            "product_code": "DM",
            "country_code": "GE",
            "date_from": "2026-06-15",
            "date_to": "2026-06-15",
        })
        assert_status(daily_metrics, 200, "daily metrics query")
        daily_rows = daily_metrics.json().get("data") or []
        assert_true(daily_rows and daily_rows[0].get("views") == 1234, "daily metrics should return seeded snapshot")

        ai_materials = client.get("/api/ai/materials", headers={"Authorization": "Bearer contract-ai-key"})
        assert_status(ai_materials, 401, "ai materials without valid key")

        feishu_preview = client.get("/api/reports/daily-feishu-preview", params={"date": "2026-06-15"})
        assert_status(feishu_preview, 200, "daily Feishu preview")
        feishu_preview_body = feishu_preview.json()
        feishu_report = feishu_preview_body.get("report", {})
        assert_true(feishu_report.get("report_date") == "2026-06-15", "Feishu preview should use requested date")
        assert_true(any(item.get("product_name") == "Demi" for item in feishu_report.get("products", [])), "Feishu preview should expose product rows")
        assert_true("Demi" in feishu_preview_body.get("message", ""), "Feishu preview should include seeded product")

        feishu_analysis = client.get("/api/reports/daily-feishu-analysis", params={"date": "2026-06-15", "model": "gpt-4.1-mini"})
        assert_status(feishu_analysis, 200, "daily Feishu analysis without LLM key")
        assert_true(feishu_analysis.json().get("needs_api_key") is True, "Feishu analysis should report missing LLM key")

        product_tag = client.post("/api/product-tags", json={"product_code": "DM", "tag": "Test Tag"})
        assert_status(product_tag, 200, "create product tag")
        assert_true("Test Tag" in product_tag.json().get("tags", []), "product tag should round trip")

        account_tag = client.post("/api/account-tags", json={"account_id": "account-dm-ge-1", "tag": "Hero"})
        assert_status(account_tag, 200, "create account tag")
        account_tags = client.get("/api/account-tags", params={"account_ids": "account-dm-ge-1"})
        assert_status(account_tags, 200, "get account tags")
        assert_true(account_tags.json().get("tags", {}).get("account-dm-ge-1") == ["Hero"], "account tag should round trip")

        account_issue = client.post("/api/account-issues", json={"account_id": "account-dm-ge-1", "issue": "Manual issue"})
        assert_status(account_issue, 200, "create account issue")
        account_issues = client.get("/api/account-issues", params={"account_ids": "account-dm-ge-1"})
        assert_status(account_issues, 200, "get account issues")
        assert_true("Manual issue" in account_issues.json().get("issues", {}).get("account-dm-ge-1", []), "account issue should round trip")

        api_key = client.post("/api/api-keys", json={"name": "Contract Key"})
        assert_status(api_key, 200, "create api key")
        api_key_body = api_key.json()
        assert_true(api_key_body.get("key", "").startswith("deca_"), "api key should return raw key once")
        key_id = (api_key_body.get("record") or {}).get("id")
        key_list = client.get("/api/api-keys")
        assert_status(key_list, 200, "list api keys")
        assert_true(any(item.get("id") == key_id for item in key_list.json().get("keys", [])), "created api key should be listed")
        ai_materials_valid = client.get(
            "/api/ai/materials",
            params={"product_code": "DM", "country_code": "GE"},
            headers={"Authorization": f"Bearer {api_key_body.get('key')}"},
        )
        assert_status(ai_materials_valid, 200, "ai materials with valid api key")
        assert_true(ai_materials_valid.json().get("totals", {}).get("materials") == 1, "ai materials should expose seeded material")
        revoked = client.post("/api/api-keys/revoke", json={"id": key_id})
        assert_status(revoked, 200, "revoke api key")
        assert_true((revoked.json().get("record") or {}).get("active") is False, "revoked api key should be inactive")

        reelfarm_config = client.post("/api/reelfarm/config", json={"api_key": "contract-rf-key"})
        assert_status(reelfarm_config, 200, "set reelfarm config")
        assert_true(reelfarm_config.json().get("configured") is True, "reelfarm config should accept api key")
        reelfarm_config_get = client.get("/api/reelfarm/config")
        assert_status(reelfarm_config_get, 200, "get reelfarm config")
        assert_true(reelfarm_config_get.json().get("configured") is True, "reelfarm config should round trip")
        reelfarm_config_clear = client.post("/api/reelfarm/config", json={"api_key": ""})
        assert_status(reelfarm_config_clear, 200, "clear reelfarm config")
        assert_true(reelfarm_config_clear.json().get("configured") is False, "reelfarm config should clear api key")

        publish_state = {
            "assignments": [
                {
                    "id": "assignment-1",
                    "person_id": "person-1",
                    "person_name": "Owner",
                    "product_id": "product-demi",
                    "country_id": "country-germany",
                }
            ]
        }
        publish_post = client.post("/api/publish-check", json={"state": publish_state})
        assert_status(publish_post, 200, "save publish check state")
        publish_get = client.get("/api/publish-check")
        assert_status(publish_get, 200, "get publish check state")
        assert_true((publish_get.json().get("state") or {}).get("assignments") == publish_state["assignments"], "publish check state should round trip")

        stored_country = client.get("/api/reelfarm/stored-country", params={"product_code": "DM", "country_code": "GE"})
        assert_status(stored_country, 200, "stored country")
        assert_true(stored_country.json().get("count") == 1, "stored country should return seeded card")

    print("api contract checks passed")


if __name__ == "__main__":
    main()
