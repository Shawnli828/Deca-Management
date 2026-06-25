from datetime import datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server_modules.account_issues import ZERO_PLAY_VIEW_THRESHOLD  # noqa: E402
from server_modules.daily_report import daily_feishu_report_text  # noqa: E402
from server_modules.time_windows import (  # noqa: E402
    business_material_date_for_utc_datetime,
    business_material_day_window,
    onboarding_date_for_utc_datetime,
    onboarding_day_window,
    parse_iso_datetime,
    previous_complete_windows,
)
from server_modules.metrics_service import (  # noqa: E402
    build_daily_report_product_item,
    daily_metric_windows,
    evaluate_sync_readiness,
    normalize_business_report_row,
    normalize_reelfarm_account_row,
    summarize_business_report_rows,
    summarize_daily_report_products,
)
from server_modules.sync_status import format_sync_readiness_line, sync_freshness_from_runs, sync_status_from_runs  # noqa: E402
from server_modules.sync_result import error_sync_result, normalized_sync_result  # noqa: E402


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main():
    material_window = business_material_day_window("2026-06-13")
    assert_equal(material_window["start_local"].isoformat(), "2026-06-12T23:59:00+08:00", "material start local")
    assert_equal(material_window["end_local"].isoformat(), "2026-06-13T23:59:00+08:00", "material end local")
    assert_equal(material_window["utc_start"].isoformat(), "2026-06-12T15:59:00+00:00", "material start utc")
    assert_equal(material_window["utc_end"].isoformat(), "2026-06-13T15:59:00+00:00", "material end utc")

    onboarding_window = onboarding_day_window("2026-06-13")
    assert_equal(onboarding_window["start_local"].isoformat(), "2026-06-12T08:00:00+08:00", "onboarding start local")
    assert_equal(onboarding_window["end_local"].isoformat(), "2026-06-13T08:00:00+08:00", "onboarding end local")
    assert_equal(onboarding_window["utc_start"].isoformat(), "2026-06-12T00:00:00+00:00", "onboarding start utc")
    assert_equal(onboarding_window["utc_end"].isoformat(), "2026-06-13T00:00:00+00:00", "onboarding end utc")

    metric_windows = daily_metric_windows("2026-06-13")
    assert_equal(metric_windows["content"]["start_local"].isoformat(), "2026-06-12T23:59:00+08:00", "daily metric content start")
    assert_equal(metric_windows["onboarding"]["start_local"].isoformat(), "2026-06-12T08:00:00+08:00", "daily metric onboarding start")

    shared_row = normalize_business_report_row(
        material_window,
        onboarding_window,
        {
            "reelfarm_materials": 2,
            "reelfarm_published_automations": 1,
            "reelfarm_posts": 2,
            "reelfarm_views": 300,
            "clone_materials": 1,
            "clone_posts": 1,
            "clone_views": 60,
            "total_views": 360,
        },
        18,
        "published_materials",
        5,
    )
    assert_equal(shared_row["reelfarm_expected_automations"], 5, "shared metrics expected automations")
    assert_equal(shared_row["download_rate"], 5.0, "shared metrics download rate")
    shared_totals = summarize_business_report_rows([shared_row])
    assert_equal(shared_totals["total_views"], 360, "shared metrics total views")
    assert_equal(shared_totals["download_rate"], 5.0, "shared metrics totals download rate")

    account_row = normalize_reelfarm_account_row({
        "post_count": "4",
        "total_views": "1000",
        "posted_account_count": "1",
        "expected_account_count": "1",
    })
    assert_equal(account_row["avg_views"], 250.0, "rf account avg views")
    assert_equal(account_row["post_count"], 4, "rf account post count normalization")

    product_item = build_daily_report_product_item(
        "DB",
        "DeenBack",
        "2026-06-13",
        shared_row,
        [{"country_code": "GE"}],
        {"missing_account_count": 2, "zero_play_account_count": 1},
        {"event": "Onboarding Step Viewed"},
    )
    product_totals = summarize_daily_report_products([product_item])
    assert_equal(product_totals["reelfarm_views"], 300, "daily report product total rf views")
    assert_equal(product_totals["missing_account_count"], 2, "daily report product missing total")
    assert_equal(product_totals["download_rate"], 5.0, "daily report product download rate")

    sync_status = sync_status_from_runs({
        "reelfarm": {
            "status": "success",
            "started_at": "2026-06-14T00:00:00+00:00",
            "finished_at": "2026-06-14T00:30:00+00:00",
            "duration_seconds": 1800,
            "records_count": 12,
            "error": "",
        }
    })
    assert_equal(sync_status["sources"]["reelfarm"]["label"], "RF", "sync status label")
    assert_equal(sync_status["sources"]["reelfarm"]["records_count"], 12, "sync status record count")
    freshness = sync_freshness_from_runs({
        "reelfarm": {
            "status": "success",
            "finished_at": "2026-06-14T00:30:00+00:00",
            "records_count": 12,
        },
        "museon_clone": {
            "status": "error",
            "finished_at": "2026-06-14T00:31:00+00:00",
            "error": "timeout",
        },
    })
    assert_equal(freshness["sources"]["reelfarm"]["state"], "fresh", "sync freshness fresh state")
    assert_equal(freshness["sources"]["museon_clone"]["state"], "error", "sync freshness error state")

    before_material_cutoff = parse_iso_datetime("2026-06-13T15:58:59+00:00")
    at_material_cutoff = parse_iso_datetime("2026-06-13T15:59:00+00:00")
    assert_equal(business_material_date_for_utc_datetime(before_material_cutoff), "2026-06-13", "material date before cutoff")
    assert_equal(business_material_date_for_utc_datetime(at_material_cutoff), "2026-06-14", "material date at cutoff")

    before_onboarding_cutoff = parse_iso_datetime("2026-06-12T23:59:59+00:00")
    at_onboarding_cutoff = parse_iso_datetime("2026-06-13T00:00:00+00:00")
    assert_equal(onboarding_date_for_utc_datetime(before_onboarding_cutoff), "2026-06-13", "onboarding date before cutoff")
    assert_equal(onboarding_date_for_utc_datetime(at_onboarding_cutoff), "2026-06-14", "onboarding date at cutoff")

    fixed_now = datetime.fromisoformat("2026-06-14T05:30:00+00:00")
    windows = previous_complete_windows(fixed_now)
    assert_equal(windows["yesterday_start"], "2026-06-12T16:00:00+00:00", "previous complete yesterday start")
    assert_equal(windows["yesterday_end"], "2026-06-13T16:00:00+00:00", "previous complete yesterday end")
    assert_equal(windows["seven_start"], "2026-06-06T16:00:00+00:00", "previous complete seven start")
    assert_equal(windows["seven_end"], "2026-06-13T16:00:00+00:00", "previous complete seven end")
    assert_equal(ZERO_PLAY_VIEW_THRESHOLD, 150, "zero play warning threshold")

    report_text = daily_feishu_report_text({
        "report_date": "2026-06-13",
        "business_window_local": {"start": "2026-06-12T23:59:00+08:00", "end": "2026-06-13T23:59:00+08:00"},
        "onboarding_window_local": {"start": "2026-06-12T08:00:00+08:00", "end": "2026-06-13T08:00:00+08:00"},
        "sync_status": {
            "sources": {
                "reelfarm": {"label": "RF", "status": "success", "finished_at": "2026-06-14T00:30:00+00:00"},
                "museon_clone": {"label": "Clone", "status": "success", "finished_at": "2026-06-14T00:31:00+00:00"},
                "growth_mixpanel": {"label": "Mixpanel", "status": "success", "finished_at": "2026-06-14T00:32:00+00:00"},
            }
        },
        "totals": {},
        "products": [],
    })
    if "数据同步：RF 2026-06-14T00:30:00+00:00 (success)" not in report_text:
        raise AssertionError("daily report sync status line is missing")
    if "同步校验：" not in report_text:
        raise AssertionError("daily report sync readiness line is missing")

    readiness_ok = evaluate_sync_readiness(
        {
            "sources": {
                "reelfarm": {"label": "RF", "status": "success", "finished_at": "2026-06-14T00:30:00+00:00"},
                "museon_clone": {"label": "Clone", "status": "success", "finished_at": "2026-06-14T00:31:00+00:00"},
                "growth_mixpanel": {"label": "Mixpanel", "status": "success", "finished_at": "2026-06-14T00:32:00+00:00"},
            }
        },
        min_finished_at="2026-06-13T15:59:00+00:00",
    )
    assert_equal(readiness_ok["ok"], True, "sync readiness success")
    assert_equal(format_sync_readiness_line(readiness_ok), "同步校验：RF / Clone / Mixpanel 已完成", "sync readiness success line")

    normalized_sync = normalized_sync_result(
        "reelfarm",
        {"ok": True, "records": [{"id": 1}, {"id": 2}]},
        started_at="2026-06-14T00:00:00+00:00",
        finished_at="2026-06-14T00:00:02+00:00",
        duration_seconds=2.0,
    )
    assert_equal(normalized_sync["source"], "reelfarm", "normalized sync source")
    assert_equal(normalized_sync["status"], "success", "normalized sync status")
    assert_equal(normalized_sync["records_count"], 2, "normalized sync records count")

    from server_modules.services import sync_runtime  # noqa: E402

    recorded_sync_runs = []
    original_safe_record_sync_run = sync_runtime.safe_record_sync_run
    sync_runtime.safe_record_sync_run = lambda *args, **kwargs: recorded_sync_runs.append((args, kwargs)) or {"ok": True}
    try:
        recorded_result = sync_runtime.run_recorded_sync(
            "reelfarm",
            lambda: {"ok": True, "records": [{"id": "rf-1"}]},
        )
        assert_equal(recorded_result["source"], "reelfarm", "recorded sync source")
        assert_equal(recorded_result["status"], "success", "recorded sync status")
        assert_equal(recorded_result["records_count"], 1, "recorded sync records count")
        assert_equal(recorded_sync_runs[0][0][0], "reelfarm", "recorded sync run source")
        assert_equal(recorded_sync_runs[0][0][1], "success", "recorded sync run status")
        assert_equal(recorded_sync_runs[0][1]["records_count"], 1, "recorded sync run records count")
        try:
            sync_runtime.run_recorded_sync("museon_clone", lambda: (_ for _ in ()).throw(RuntimeError("timeout")))
        except RuntimeError:
            pass
        else:
            raise AssertionError("recorded sync should re-raise runner failures")
        assert_equal(recorded_sync_runs[1][0][0], "museon_clone", "failed recorded sync run source")
        assert_equal(recorded_sync_runs[1][0][1], "error", "failed recorded sync run status")
    finally:
        sync_runtime.safe_record_sync_run = original_safe_record_sync_run

    failed_sync = error_sync_result("museon_clone", "timeout")
    assert_equal(failed_sync["ok"], False, "failed sync ok flag")
    assert_equal(failed_sync["status"], "error", "failed sync status")
    assert_equal(failed_sync["errors"][0]["error"], "timeout", "failed sync error")

    readiness_stale = evaluate_sync_readiness(
        {
            "sources": {
                "reelfarm": {"label": "RF", "status": "success", "finished_at": "2026-06-13T00:30:00+00:00"},
                "museon_clone": {"label": "Clone", "status": "error", "finished_at": "2026-06-14T00:31:00+00:00", "error": "timeout"},
                "growth_mixpanel": {"label": "Mixpanel", "status": "success", "finished_at": "2026-06-14T00:32:00+00:00"},
            }
        },
        min_finished_at="2026-06-13T15:59:00+00:00",
    )
    assert_equal(readiness_stale["ok"], False, "sync readiness stale")
    stale_line = format_sync_readiness_line(readiness_stale)
    if "RF 同步时间早于统计窗口结束" not in stale_line or "Clone 最近同步状态不是 success" not in stale_line:
        raise AssertionError("sync readiness warning line is incomplete")

    print("smoke checks passed")


if __name__ == "__main__":
    main()
