def collect_numeric_values(value):
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        values = []
        for child in value.values():
            values.extend(collect_numeric_values(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(collect_numeric_values(child))
        return values
    return []


def mixpanel_segmentation_unique_from_payload(payload, event_name):
    if not isinstance(payload, dict):
        return 0
    data = payload.get("data")
    if isinstance(data, dict):
        values = data.get("values")
        if isinstance(values, dict):
            candidate = values.get(event_name)
            if candidate is None and len(values) == 1:
                candidate = next(iter(values.values()))
            return int(round(sum(collect_numeric_values(candidate))))
    results = payload.get("results")
    if isinstance(results, dict):
        return int(round(sum(collect_numeric_values(results))))
    return 0
