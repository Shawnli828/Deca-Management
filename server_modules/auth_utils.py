import hashlib
import hmac
import time


def cron_authorized(headers, secret):
    if not secret:
        return True
    return headers.get("Authorization", "") == f"Bearer {secret}"


def password_hash(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def auth_signature(username, expires_at, session_secret):
    payload = f"{username}|{expires_at}"
    return hmac.new(session_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def make_auth_token(username, session_secret, ttl_seconds, now=None):
    current_time = int(now if now is not None else time.time())
    expires_at = current_time + int(ttl_seconds)
    signature = auth_signature(username, expires_at, session_secret)
    return f"{username}|{expires_at}|{signature}"


def valid_auth_token(token, admin_username, session_secret, now=None):
    try:
        username, expires_at_text, signature = str(token or "").split("|", 2)
        expires_at = int(expires_at_text)
    except (TypeError, ValueError):
        return False

    current_time = int(now if now is not None else time.time())
    if username != admin_username or expires_at < current_time:
        return False

    expected = auth_signature(username, expires_at, session_secret)
    return hmac.compare_digest(signature, expected)


def cookie_header(name, value, max_age=None):
    parts = [
        f"{name}={value}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if max_age is not None:
        parts.append(f"Max-Age={int(max_age)}")
    return "; ".join(parts)
