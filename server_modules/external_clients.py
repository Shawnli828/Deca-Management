import base64
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timezone
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


def daily_feishu_llm_api_key(env):
    return (
        env.get("LLM_API_KEY", "").strip()
        or env.get("OPENAI_API_KEY", "").strip()
    )


def daily_feishu_llm_model(model="", env=None, default_model=""):
    env = env or {}
    value = str(model or "").strip() or env.get("LLM_MODEL", "").strip() or default_model
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,96}", value):
        return default_model
    return value


def fallback_llm_models(env, default_model, fallback_models):
    models = []
    configured_model = env.get("LLM_MODEL", "").strip() or default_model
    if configured_model:
        models.append(configured_model)
    models.extend(fallback_models)
    return list(dict.fromkeys(models))


def selectable_gpt_model(model_id):
    value = str(model_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,128}", value):
        return False
    if not value.startswith("gpt-"):
        return False
    lowered = value.lower()
    blocked_fragments = (
        "audio",
        "image",
        "realtime",
        "search-preview",
        "transcribe",
        "tts",
        "vision",
    )
    return not any(fragment in lowered for fragment in blocked_fragments)


def sort_llm_models(models, preferred):
    preferred_index = {model: index for index, model in enumerate(preferred)}
    return sorted(
        list(dict.fromkeys(models)),
        key=lambda model: (
            preferred_index.get(model, len(preferred)),
            model,
        ),
    )


def llm_models_payload(api_key, api_base, selected_default, fallback_models, default_model, ssl_context_factory=None):
    generated_at = datetime.now(timezone.utc).isoformat()
    if not api_key:
        return {
            "ok": True,
            "configured": False,
            "needs_api_key": True,
            "fallback": True,
            "models": fallback_models,
            "default_model": selected_default,
            "generated_at": generated_at,
        }

    endpoint = f"{api_base}/models"
    request = Request(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    context = ssl_context_factory() if ssl_context_factory else None
    try:
        with urlopen(request, timeout=20, context=context) as response:
            raw = response.read().decode("utf-8", errors="replace")
        payload = json.loads(raw)
        models = [
            str(item.get("id", "")).strip()
            for item in payload.get("data", [])
            if isinstance(item, dict) and selectable_gpt_model(item.get("id"))
        ]
        models = sort_llm_models(models or fallback_models, fallback_models)
        if selected_default not in models:
            selected_default = models[0] if models else default_model
        return {
            "ok": True,
            "configured": True,
            "needs_api_key": False,
            "fallback": False,
            "models": models,
            "default_model": selected_default,
            "generated_at": generated_at,
        }
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        error = f"LLM models API returned HTTP {exc.code}: {detail[:300]}"
    except URLError as exc:
        error = f"Could not reach LLM models API: {exc.reason}"
    except Exception as exc:
        error = f"Could not load LLM models: {exc}"

    return {
        "ok": True,
        "configured": True,
        "needs_api_key": False,
        "fallback": True,
        "models": fallback_models,
        "default_model": selected_default,
        "error": error,
        "generated_at": generated_at,
    }


def call_daily_feishu_llm(messages, api_key, api_base, selected_model, ssl_context_factory=None):
    if not api_key:
        return {
            "ok": True,
            "configured": False,
            "needs_api_key": True,
            "model": selected_model,
            "analysis": "需要在后端环境变量配置 LLM_API_KEY 或 OPENAI_API_KEY 后，才能生成 AI 分析。",
        }

    endpoint = f"{api_base}/chat/completions"
    request_payloads = [
        {
            "model": selected_model,
            "messages": messages,
            "max_completion_tokens": 1200,
        },
        {
            "model": selected_model,
            "messages": messages,
            "max_tokens": 1200,
        },
    ]
    last_http_error = None
    context = ssl_context_factory() if ssl_context_factory else None
    try:
        raw = ""
        for payload in request_payloads:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request = Request(
                endpoint,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=45, context=context) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                last_http_error = None
                break
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_http_error = (exc.code, detail)
                if exc.code == 400 and "max_completion_tokens" in payload and "max_completion_tokens" in detail:
                    continue
                if exc.code == 400 and "max_tokens" in payload and "max_tokens" in detail:
                    continue
                raise
        if last_http_error:
            code, detail = last_http_error
            return {"ok": False, "error": f"LLM API returned HTTP {code}: {detail[:500]}", "model": selected_model}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"LLM API returned HTTP {exc.code}: {detail[:500]}", "model": selected_model}
    except URLError as exc:
        return {"ok": False, "error": f"Could not reach LLM API: {exc.reason}", "model": selected_model}
    except Exception as exc:
        return {"ok": False, "error": f"LLM analysis failed: {exc}", "model": selected_model}

    try:
        payload = json.loads(raw)
        analysis = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
    except (json.JSONDecodeError, AttributeError, IndexError):
        analysis = ""
    if not analysis:
        return {"ok": False, "error": "LLM API returned an empty analysis.", "model": selected_model}
    return {
        "ok": True,
        "configured": True,
        "needs_api_key": False,
        "model": selected_model,
        "analysis": analysis,
    }
