from datetime import datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server import (  # noqa: E402
    business_material_date_for_utc_datetime,
    business_material_day_window,
    onboarding_date_for_utc_datetime,
    onboarding_day_window,
    parse_iso_datetime,
    previous_complete_windows,
)


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

    print("smoke checks passed")


if __name__ == "__main__":
    main()
