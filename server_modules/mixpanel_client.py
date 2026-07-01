import base64
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from server_modules.mixpanel_utils import mixpanel_distinct_id, mixpanel_export_base_url


def _mixpanel_config_values(config, default_region):
    config = config or {}
    return (
        config.get("project_id", ""),
        config.get("username", ""),
        config.get("secret", ""),
        config.get("region", default_region),
    )


def _mixpanel_export_payload(
    config,
    event_name,
    utc_start,
    utc_end,
    *,
    default_region,
    mixpanel_timezone,
    source_dates_for_utc_window,
    make_ssl_context,
    error_prefix,
    where_expression=None,
):
    project_id, username, secret, region = _mixpanel_config_values(config, default_region)
    if not project_id or not username or not secret or not event_name:
        return None

    source_date_from, source_date_to = source_dates_for_utc_window(
        utc_start,
        utc_end,
        mixpanel_timezone(),
        clamp_to_today=True,
    )
    if not source_date_from or source_date_from > source_date_to:
        return ""

    params_payload = {
        "project_id": project_id,
        "event": json.dumps([event_name], ensure_ascii=False),
        "from_date": source_date_from,
        "to_date": source_date_to,
    }
    if where_expression:
        params_payload["where"] = where_expression
    params = urlencode(params_payload)
    credentials = f"{username}:{secret}".encode("utf-8")
    request = Request(
        f"{mixpanel_export_base_url(region)}?{params}",
        headers={
            "Authorization": "Basic " + base64.b64encode(credentials).decode("ascii"),
            "Accept": "text/plain",
        },
    )
    try:
        with urlopen(request, timeout=60, context=make_ssl_context()) as response:
            return response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:240]
        raise RuntimeError(f"{error_prefix}: {error.code} {detail}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"{error_prefix}: {error}") from error


def _iter_mixpanel_events(payload, event_name, utc_start, utc_end):
    start_epoch = int(utc_start.timestamp())
    end_epoch = int(utc_end.timestamp())
    for line in (payload or "").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("event") != event_name:
            continue
        properties = event.get("properties") if isinstance(event, dict) else {}
        if not isinstance(properties, dict):
            properties = {}
        raw_time = properties.get("time", event.get("time") if isinstance(event, dict) else None)
        try:
            timestamp = float(raw_time)
        except (TypeError, ValueError):
            continue
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        if timestamp < start_epoch or timestamp >= end_epoch:
            continue
        yield event, properties, datetime.fromtimestamp(timestamp, timezone.utc)


def mixpanel_event_daily_counts(
    config,
    event_name,
    utc_start,
    utc_end,
    value_type="general",
    *,
    default_region,
    mixpanel_timezone,
    source_dates_for_utc_window,
    report_date_for_utc_datetime,
    make_ssl_context,
):
    payload = _mixpanel_export_payload(
        config,
        event_name,
        utc_start,
        utc_end,
        default_region=default_region,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        make_ssl_context=make_ssl_context,
        error_prefix="Mixpanel query failed",
    )
    if payload is None:
        return {}

    totals = {}
    unique_ids = {}
    for event, properties, event_datetime in _iter_mixpanel_events(payload, event_name, utc_start, utc_end):
        report_date = report_date_for_utc_datetime(event_datetime)
        if not report_date:
            continue
        totals[report_date] = totals.get(report_date, 0) + 1
        distinct_id = mixpanel_distinct_id(event, properties)
        if distinct_id:
            unique_ids.setdefault(report_date, set()).add(distinct_id)
    if value_type == "unique":
        return {report_date: len(ids) for report_date, ids in unique_ids.items()}
    return totals


def mixpanel_event_business_material_counts(
    config,
    event_name,
    utc_start,
    utc_end,
    value_type="general",
    date_mapper=None,
    *,
    default_region,
    mixpanel_timezone,
    source_dates_for_utc_window,
    business_material_date_for_utc_datetime,
    make_ssl_context,
):
    payload = _mixpanel_export_payload(
        config,
        event_name,
        utc_start,
        utc_end,
        default_region=default_region,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        make_ssl_context=make_ssl_context,
        error_prefix="Mixpanel query failed",
    )
    if payload is None:
        return {}

    totals = {}
    unique_ids = {}
    mapper = date_mapper or business_material_date_for_utc_datetime
    for event, properties, event_datetime in _iter_mixpanel_events(payload, event_name, utc_start, utc_end):
        report_date = mapper(event_datetime)
        if not report_date:
            continue
        totals[report_date] = totals.get(report_date, 0) + 1
        distinct_id = mixpanel_distinct_id(event, properties)
        if distinct_id:
            unique_ids.setdefault(report_date, set()).add(distinct_id)
    if value_type == "unique":
        return {report_date: len(ids) for report_date, ids in unique_ids.items()}
    return totals


def mixpanel_event_user_unique_query_count(
    config,
    event_name,
    utc_start,
    utc_end,
    *,
    default_region,
    mixpanel_timezone,
    source_dates_for_utc_window,
    make_ssl_context,
):
    payload = _mixpanel_export_payload(
        config,
        event_name,
        utc_start,
        utc_end,
        default_region=default_region,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        make_ssl_context=make_ssl_context,
        error_prefix="Mixpanel Export API failed",
    )
    if payload is None:
        return None

    unique_ids = set()
    for event, properties, _event_datetime in _iter_mixpanel_events(payload, event_name, utc_start, utc_end):
        distinct_id = mixpanel_distinct_id(event, properties)
        if distinct_id:
            unique_ids.add(distinct_id)
    return len(unique_ids)


def mixpanel_event_user_unique_filtered_count(
    config,
    event_name,
    utc_start,
    utc_end,
    property_filter,
    *,
    default_region,
    mixpanel_timezone,
    source_dates_for_utc_window,
    make_ssl_context,
    where_expression=None,
):
    payload = _mixpanel_export_payload(
        config,
        event_name,
        utc_start,
        utc_end,
        default_region=default_region,
        mixpanel_timezone=mixpanel_timezone,
        source_dates_for_utc_window=source_dates_for_utc_window,
        make_ssl_context=make_ssl_context,
        error_prefix="Mixpanel Export API failed",
        where_expression=where_expression,
    )
    if payload is None:
        return {"count": None, "filter_supported": False, "scanned": 0, "filter_method": "none"}

    if where_expression:
        unique_ids = set()
        scanned = 0
        for event, properties, _event_datetime in _iter_mixpanel_events(payload, event_name, utc_start, utc_end):
            scanned += 1
            distinct_id = mixpanel_distinct_id(event, properties)
            if distinct_id:
                unique_ids.add(distinct_id)
        if scanned:
            return {
                "count": len(unique_ids),
                "filter_supported": True,
                "scanned": scanned,
                "filter_method": "export_where",
            }

        # A zero-row server-side filter can mean either a true zero or that the
        # project uses a different country property. Fall back to a local scan so
        # the caller can still distinguish unsupported filters from zero counts.
        payload = _mixpanel_export_payload(
            config,
            event_name,
            utc_start,
            utc_end,
            default_region=default_region,
            mixpanel_timezone=mixpanel_timezone,
            source_dates_for_utc_window=source_dates_for_utc_window,
            make_ssl_context=make_ssl_context,
            error_prefix="Mixpanel Export API failed",
        )

    unique_ids = set()
    filter_supported = False
    scanned = 0
    for event, properties, _event_datetime in _iter_mixpanel_events(payload, event_name, utc_start, utc_end):
        scanned += 1
        filter_result = property_filter(properties)
        if isinstance(filter_result, tuple):
            matched, supported = filter_result
        else:
            matched, supported = bool(filter_result), bool(filter_result)
        filter_supported = filter_supported or bool(supported)
        if not matched:
            continue
        distinct_id = mixpanel_distinct_id(event, properties)
        if distinct_id:
            unique_ids.add(distinct_id)
    return {
        "count": len(unique_ids),
        "filter_supported": filter_supported,
        "scanned": scanned,
        "filter_method": "local_scan",
    }
