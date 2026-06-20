import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FEISHU_OPEN_API_BASE = "https://open.feishu.cn/open-apis"


def _post_json(endpoint, payload, headers=None, ssl_context_factory=None, timeout=15):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    context = ssl_context_factory() if ssl_context_factory else None
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"Feishu returned HTTP {exc.code}: {detail[:500]}"}
    except URLError as exc:
        return {"ok": False, "error": f"Could not reach Feishu OpenAPI: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": f"Feishu OpenAPI request failed: {exc}"}

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {"ok": False, "error": f"Feishu returned non-JSON response: {raw[:300]}"}

    code = data.get("code", 0)
    if code not in (0, "0", None):
        return {"ok": False, "error": data.get("msg") or raw[:500], "response": data}
    return {"ok": True, "response": data}


def feishu_template_content(template_id, template_version, template_variables):
    return json.dumps(
        {
            "type": "template",
            "data": {
                "template_id": template_id,
                "template_version_name": template_version,
                "template_variable": template_variables or {},
            },
        },
        ensure_ascii=False,
    )


def feishu_template_card_response(template_id, template_version, template_variables):
    return {
        "type": "template",
        "data": {
            "template_id": template_id,
            "template_version_name": template_version,
            "template_variable": template_variables or {},
        },
    }


def tenant_access_token(app_id, app_secret, ssl_context_factory=None):
    app_id = str(app_id or "").strip()
    app_secret = str(app_secret or "").strip()
    if not app_id or not app_secret:
        return {"ok": False, "error": "FEISHU_APP_ID and FEISHU_APP_SECRET are required."}

    result = _post_json(
        f"{FEISHU_OPEN_API_BASE}/auth/v3/tenant_access_token/internal",
        {"app_id": app_id, "app_secret": app_secret},
        ssl_context_factory=ssl_context_factory,
    )
    if not result.get("ok"):
        return result
    token = (result.get("response") or {}).get("tenant_access_token")
    if not token:
        return {"ok": False, "error": "Feishu did not return tenant_access_token.", "response": result.get("response")}
    return {"ok": True, "tenant_access_token": token, "response": result.get("response")}


def send_template_card(
    *,
    app_id,
    app_secret,
    chat_id,
    template_id,
    template_version,
    template_variables,
    ssl_context_factory=None,
):
    chat_id = str(chat_id or "").strip()
    template_id = str(template_id or "").strip()
    template_version = str(template_version or "").strip()
    if not chat_id:
        return {"ok": False, "error": "FEISHU_CHAT_ID is required."}
    if not template_id or not template_version:
        return {"ok": False, "error": "Feishu template id and version are required."}

    token_result = tenant_access_token(app_id, app_secret, ssl_context_factory)
    if not token_result.get("ok"):
        return token_result

    query = urlencode({"receive_id_type": "chat_id"})
    result = _post_json(
        f"{FEISHU_OPEN_API_BASE}/im/v1/messages?{query}",
        {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": feishu_template_content(template_id, template_version, template_variables),
        },
        headers={"Authorization": f"Bearer {token_result.get('tenant_access_token')}"},
        ssl_context_factory=ssl_context_factory,
    )
    if not result.get("ok"):
        return result
    response = result.get("response") or {}
    return {
        "ok": True,
        "message_id": ((response.get("data") or {}).get("message_id")),
        "response": response,
    }
