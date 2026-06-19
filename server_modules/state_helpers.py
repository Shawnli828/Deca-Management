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


def default_publish_check_state():
    return {"assignments": [], "last_result": None}


def parse_publish_check_state(raw):
    if not raw:
        return default_publish_check_state()
    try:
        state = json.loads(raw)
    except json.JSONDecodeError:
        return default_publish_check_state()
    if not isinstance(state, dict):
        return default_publish_check_state()
    assignments = state.get("assignments")
    if not isinstance(assignments, list):
        assignments = []
    return {
        "assignments": assignments,
        "last_result": state.get("last_result") if isinstance(state.get("last_result"), dict) else None,
    }


def clean_publish_check_state(state, generate_id):
    clean = default_publish_check_state()
    assignments = state.get("assignments") if isinstance(state, dict) else []
    if isinstance(assignments, list):
        clean["assignments"] = [
            {
                "id": str(item.get("id") or generate_id()),
                "person_id": str(item.get("person_id") or ""),
                "person_name": str(item.get("person_name") or ""),
                "product_id": str(item.get("product_id") or ""),
                "country_id": str(item.get("country_id") or ""),
            }
            for item in assignments
            if isinstance(item, dict) and item.get("product_id") and item.get("country_id")
        ]
    if isinstance(state, dict) and isinstance(state.get("last_result"), dict):
        clean["last_result"] = state["last_result"]
    return clean


def data_source_channel_code(source):
    return "MUSEON_CLONE" if str(source or "").strip().lower() in {"museon_clone", "clone", "museon"} else "TIKTOK"
