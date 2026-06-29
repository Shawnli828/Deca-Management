import os
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


BUSINESS_TIMEZONE = timezone(timedelta(hours=8))
REPORT_TIMEZONE_NAME = os.environ.get("REPORT_TIMEZONE", "Asia/Shanghai").strip()
MIXPANEL_TIMEZONE_NAME = os.environ.get("MIXPANEL_TIMEZONE", "America/Los_Angeles").strip()


def parse_iso_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    raw_value = str(value).strip()
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def utc_date_string(value=None):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date().isoformat()
    parsed = parse_iso_datetime(value)
    if parsed:
        return parsed.astimezone(timezone.utc).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def business_date_string(value=None):
    if isinstance(value, datetime):
        return value.astimezone(BUSINESS_TIMEZONE).date().isoformat()
    parsed = parse_iso_datetime(value)
    if parsed:
        return parsed.astimezone(BUSINESS_TIMEZONE).date().isoformat()
    return datetime.now(BUSINESS_TIMEZONE).date().isoformat()


def previous_complete_windows(now_utc=None):
    current_local = (now_utc or datetime.now(timezone.utc)).astimezone(BUSINESS_TIMEZONE)
    today_start_local = datetime(current_local.year, current_local.month, current_local.day, tzinfo=BUSINESS_TIMEZONE)
    yesterday_start_local = today_start_local - timedelta(days=1)
    seven_start_local = yesterday_start_local - timedelta(days=6)
    return {
        "yesterday_start": yesterday_start_local.astimezone(timezone.utc).isoformat(),
        "yesterday_end": today_start_local.astimezone(timezone.utc).isoformat(),
        "seven_start": seven_start_local.astimezone(timezone.utc).isoformat(),
        "seven_end": today_start_local.astimezone(timezone.utc).isoformat(),
    }


def rolling_business_days_utc_window(days, now_utc=None, tz=None):
    tz = tz or BUSINESS_TIMEZONE
    day_count = max(1, min(366, int(days or 1)))
    current_local = (now_utc or datetime.now(timezone.utc)).astimezone(tz)
    today_start_local = datetime(current_local.year, current_local.month, current_local.day, tzinfo=tz)
    start_local = today_start_local - timedelta(days=day_count)
    return start_local.astimezone(timezone.utc).isoformat(), today_start_local.astimezone(timezone.utc).isoformat()


def rolling_snapshot_date_window(days, today_utc=None):
    day_count = max(1, min(366, int(days or 1)))
    if isinstance(today_utc, datetime):
        end = today_utc.astimezone(timezone.utc).date()
    elif today_utc:
        parsed = parse_iso_datetime(today_utc)
        end = parsed.astimezone(timezone.utc).date() if parsed else datetime.now(timezone.utc).date()
    else:
        end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=day_count - 1)
    return start.isoformat(), end.isoformat()


def named_timezone(name, fallback):
    if ZoneInfo:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    return fallback


def report_timezone():
    return named_timezone(REPORT_TIMEZONE_NAME, BUSINESS_TIMEZONE)


def mixpanel_timezone():
    return named_timezone(MIXPANEL_TIMEZONE_NAME, timezone(timedelta(hours=-7)))


def report_day_window(report_date="", tz=None):
    tz = tz or report_timezone()
    if report_date:
        date_value = datetime.strptime(str(report_date), "%Y-%m-%d").date()
    else:
        current_local = datetime.now(timezone.utc).astimezone(tz)
        date_value = (datetime(current_local.year, current_local.month, current_local.day, tzinfo=tz) - timedelta(days=1)).date()
    start_local = datetime(date_value.year, date_value.month, date_value.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return {
        "report_date": date_value.isoformat(),
        "report_timezone": getattr(tz, "key", REPORT_TIMEZONE_NAME),
        "start_local": start_local,
        "end_local": end_local,
        "utc_start": start_local.astimezone(timezone.utc),
        "utc_end": end_local.astimezone(timezone.utc),
    }


def business_material_day_window(report_date="", tz=None):
    tz = tz or report_timezone()
    if report_date:
        date_value = datetime.strptime(str(report_date), "%Y-%m-%d").date()
    else:
        date_value = datetime.now(timezone.utc).astimezone(tz).date()
    day_start = datetime(date_value.year, date_value.month, date_value.day, tzinfo=tz)
    start_local = day_start - timedelta(minutes=1)
    end_local = day_start + timedelta(days=1) - timedelta(minutes=1)
    return {
        "report_date": date_value.isoformat(),
        "report_timezone": getattr(tz, "key", REPORT_TIMEZONE_NAME),
        "start_local": start_local,
        "end_local": end_local,
        "utc_start": start_local.astimezone(timezone.utc),
        "utc_end": end_local.astimezone(timezone.utc),
    }


def onboarding_day_window(report_date="", tz=None):
    tz = tz or report_timezone()
    if report_date:
        date_value = datetime.strptime(str(report_date), "%Y-%m-%d").date()
    else:
        date_value = datetime.now(timezone.utc).astimezone(tz).date()
    day_start = datetime(date_value.year, date_value.month, date_value.day, tzinfo=tz)
    start_local = day_start - timedelta(days=1) + timedelta(hours=8)
    end_local = day_start + timedelta(hours=8)
    return {
        "report_date": date_value.isoformat(),
        "report_timezone": getattr(tz, "key", REPORT_TIMEZONE_NAME),
        "start_local": start_local,
        "end_local": end_local,
        "utc_start": start_local.astimezone(timezone.utc),
        "utc_end": end_local.astimezone(timezone.utc),
    }


def business_material_report_windows(date_from="", date_to="", days=7):
    tz = report_timezone()
    today = datetime.now(timezone.utc).astimezone(tz).date()
    try:
        if date_to:
            end_date = datetime.strptime(str(date_to), "%Y-%m-%d").date()
        else:
            end_date = today
    except ValueError:
        end_date = today
    try:
        if date_from:
            start_date = datetime.strptime(str(date_from), "%Y-%m-%d").date()
        else:
            try:
                day_count = int(days)
            except (TypeError, ValueError):
                day_count = 7
            day_count = max(1, min(90, day_count))
            start_date = end_date - timedelta(days=day_count - 1)
    except ValueError:
        start_date = end_date - timedelta(days=6)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    if (end_date - start_date).days > 89:
        start_date = end_date - timedelta(days=89)
    windows = []
    current = start_date
    while current <= end_date:
        windows.append(business_material_day_window(current.isoformat(), tz))
        current += timedelta(days=1)
    return windows


def source_dates_for_utc_window(utc_start, utc_end, source_tz, clamp_to_today=False):
    start_source = utc_start.astimezone(source_tz).date()
    end_source = (utc_end - timedelta(microseconds=1)).astimezone(source_tz).date()
    if clamp_to_today:
        today_source = datetime.now(timezone.utc).astimezone(source_tz).date()
        if end_source > today_source:
            end_source = today_source
    return start_source.isoformat(), end_source.isoformat()


def growth_report_windows(days):
    tz = report_timezone()
    current_local = datetime.now(timezone.utc).astimezone(tz)
    today_start = datetime(current_local.year, current_local.month, current_local.day, tzinfo=tz)
    windows = []
    for offset in range(days, 0, -1):
        report_date = (today_start - timedelta(days=offset)).date().isoformat()
        windows.append(report_day_window(report_date, tz))
    return windows


def report_date_for_utc_datetime(value, tz=None):
    tz = tz or report_timezone()
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz).date().isoformat()


def business_material_date_for_utc_datetime(value, tz=None):
    tz = tz or report_timezone()
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local_value = value.astimezone(tz)
    cutoff = local_value.replace(hour=23, minute=59, second=0, microsecond=0)
    if local_value >= cutoff:
        return (local_value.date() + timedelta(days=1)).isoformat()
    return local_value.date().isoformat()


def onboarding_date_for_utc_datetime(value, tz=None):
    tz = tz or report_timezone()
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local_value = value.astimezone(tz)
    cutoff = local_value.replace(hour=8, minute=0, second=0, microsecond=0)
    if local_value >= cutoff:
        return (local_value.date() + timedelta(days=1)).isoformat()
    return local_value.date().isoformat()
