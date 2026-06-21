import base64
import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def feishu_signed_payload(message, webhook_secret=""):
    payload = {
        "msg_type": "text",
        "content": {"text": message},
    }
    if webhook_secret:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{webhook_secret}"
        sign = base64.b64encode(
            hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        ).decode("utf-8")
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    return payload


def feishu_signed_card_payload(card, webhook_secret=""):
    payload = {
        "msg_type": "interactive",
        "card": card,
    }
    if webhook_secret:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{webhook_secret}"
        sign = base64.b64encode(
            hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        ).decode("utf-8")
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    return payload


def send_feishu_payload(payload, webhook_url, ssl_context_factory=None):
    if not webhook_url:
        return {"ok": False, "error": "FEISHU_WEBHOOK_URL is not configured."}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    context = ssl_context_factory() if ssl_context_factory else None
    try:
        with urlopen(request, timeout=12, context=context) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"Feishu returned HTTP {exc.code}: {detail[:300]}"}
    except URLError as exc:
        return {"ok": False, "error": f"Could not reach Feishu webhook: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": f"Feishu send failed: {exc}"}

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"raw": raw}
    code = payload.get("code", payload.get("StatusCode", 0))
    if code not in (0, "0", None):
        return {"ok": False, "error": payload.get("msg") or payload.get("StatusMessage") or raw[:300], "response": payload}
    return {"ok": True, "response": payload}


def send_feishu_message(message, webhook_url, webhook_secret="", ssl_context_factory=None):
    return send_feishu_payload(
        feishu_signed_payload(message, webhook_secret),
        webhook_url,
        ssl_context_factory,
    )


def send_feishu_card(card, webhook_url, webhook_secret="", ssl_context_factory=None):
    return send_feishu_payload(
        feishu_signed_card_payload(card, webhook_secret),
        webhook_url,
        ssl_context_factory,
    )
