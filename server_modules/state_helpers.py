import json


def default_data(generate_id):
    return [
        {
            "id": generate_id(),
            "name": "Product A",
            "logo": "",
            "countries": [
                {
                    "id": generate_id(),
                    "name": "United States",
                    "concepts": [
                        {"id": generate_id(), "name": "Tech Focus", "count": 45},
                        {"id": generate_id(), "name": "Lifestyle", "count": 30},
                    ],
                },
                {
                    "id": generate_id(),
                    "name": "Japan",
                    "concepts": [
                        {"id": generate_id(), "name": "Design/Aesthetics", "count": 50},
                    ],
                },
            ],
        },
        {
            "id": generate_id(),
            "name": "Product B",
            "logo": "",
            "countries": [
                {
                    "id": generate_id(),
                    "name": "Germany",
                    "concepts": [
                        {"id": generate_id(), "name": "Efficiency", "count": 28},
                        {"id": generate_id(), "name": "Sustainability", "count": 18},
                    ],
                }
            ],
        },
    ]


def initial_data(seed_data_path, generate_id):
    if seed_data_path.is_file():
        try:
            payload = json.loads(seed_data_path.read_text(encoding="utf-8"))
            data = payload.get("data")
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError):
            pass

    return default_data(generate_id)


def strip_reelfarm_state(value):
    if isinstance(value, list):
        return [strip_reelfarm_state(item) for item in value]
    if not isinstance(value, dict):
        return value

    clean = {}
    for key, item in value.items():
        if key == "reelFarmResult":
            continue
        clean[key] = strip_reelfarm_state(item)
    return clean


def data_source_channel_code(source):
    return "MUSEON_CLONE" if str(source or "").strip().lower() in {"museon_clone", "clone", "museon"} else "TIKTOK"
