"""
Idempotency Middleware

ASGI middleware that ensures duplicate requests (identified by X-Idempotency-Key)
are processed only once. Cached responses are replayed for subsequent identical requests.

Redis-backed storage with configurable TTLs per endpoint pattern.
Safe for concurrent requests via Redis SETNX locking.
"""

import json
import hashlib
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
import redis.asyncio as redis

from app.database import get_redis_client


IDEMPOTENCY_KEY_HEADER = "X-Idempotency-Key"
IDEMPOTENCY_RESPONSE_HEADER = "X-Idempotency-Replayed"

API_PREFIXES = ("/api/v1", "/api/v2", "/api")

TTL_BY_PATH: dict[str, int] = {
    "/auth/register": 86400,
    "/auth/reset-password": 3600,
    "/auth/me/password": 3600,
    "/auth/me/delete": 86400,
    "/auth/google/callback": 86400,
    "/analysis/upload": 3600,
    "/providers/": 300,
    "/gmail/": 300,
    "/admin/model/retrain": 3600,
    "/admin/users/": 3600,
    "/activate/complete": 86400,
    "/auth/mfa/": 3600,
    "/auth/login": 600,
    "/auth/forgot-password": 600,
    "/auth/me/avatar": 600,
    "/email/": 600,
    "/notifications/subscribe": 300,
    "/notifications/preferences": 300,
}

DEFAULT_TTL = 3600


def _strip_api_prefix(path: str) -> str:
    for prefix in API_PREFIXES:
        if path.startswith(prefix):
            return path[len(prefix):]
    return path


def _get_ttl(path: str) -> int:
    stripped = _strip_api_prefix(path)
    for prefix, ttl in TTL_BY_PATH.items():
        if stripped.startswith(prefix):
            return ttl
    return DEFAULT_TTL


class IdempotencyMiddleware:
    """ASGI middleware for request idempotency using Redis."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        if request.method not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        idempotency_key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
        if not idempotency_key:
            await self.app(scope, receive, send)
            return

        redis_client = get_redis_client()

        request_body = b""
        captured_body = []
        captured_start = {}
        body_message = None

        async def receive_wrapper():
            nonlocal body_message
            if body_message is not None:
                msg = body_message
                body_message = None
                return msg
            return await receive()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                captured_start["status"] = message.get("status", 200)
                captured_start["headers"] = {
                    k.decode(): v.decode()
                    for k, v in message.get("headers", [])
                }
                await send({
                    "type": "http.response.start",
                    "status": message.get("status", 200),
                    "headers": [
                        (k, v)
                        for k, v in message.get("headers", [])
                        if k.lower() != b"x-idempotency-replayed"
                    ] + [(IDEMPOTENCY_RESPONSE_HEADER.encode(), b"true")],
                })
            elif message["type"] == "http.response.body":
                body_chunk = message.get("body", b"")
                captured_body.append(body_chunk)
                await send(message)

        def _build_cache_key(uid: str) -> str:
            return f"idempotency:{uid}:{idempotency_key}"

        async def _replay_cached(cache_key: str) -> bool:
            cached = await redis_client.get(cache_key)
            if cached:
                cached_data = json.loads(cached)
                status_code = cached_data.get("status_code", 200)
                body = cached_data.get("body", "")

                headers_to_send = [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (IDEMPOTENCY_RESPONSE_HEADER.encode(), b"true"),
                ]
                if cached_data.get("headers"):
                    for k, v in cached_data["headers"].items():
                        headers_to_send.append(
                            (k.lower().encode(), v.encode())
                        )

                await send({
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": headers_to_send,
                })
                await send({
                    "type": "http.response.body",
                    "body": body.encode(),
                })
                return True
            return False

        async def _cache_response(cache_key: str, ttl: int):
            if captured_start:
                full_body = b"".join(captured_body).decode("utf-8", errors="replace")
                cache_data = {
                    "status_code": captured_start["status"],
                    "body": full_body,
                    "headers": captured_start["headers"],
                }
                await redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(cache_data),
                )

        async def _run_with_lock(cache_key: str):
            lock_key = f"{cache_key}:lock"
            acquired = await redis_client.set(lock_key, "1", nx=True, ex=30)
            if not acquired:
                await redis_client.expire(lock_key, 30)
                await self.app(scope, receive_wrapper, send)
                return

            request.state.idempotency_key = idempotency_key
            request.state.idempotency_cache_key = cache_key

            await self.app(scope, receive_wrapper, send_wrapper)
            await _cache_response(cache_key, _get_ttl(request.url.path))

            try:
                await redis_client.delete(lock_key)
            except Exception:
                pass

        try:
            msg = await receive()
            if msg["type"] == "http.request":
                request_body = msg.get("body", b"")
                body_message = msg

            user_id = getattr(request.state, "user_id", None)

            if user_id is None:
                body_hash = hashlib.sha256(request_body).hexdigest()[:12]
                cache_key = _build_cache_key(body_hash)
                if await _replay_cached(cache_key):
                    return
                await self.app(scope, receive_wrapper, send_wrapper)
                await _cache_response(cache_key, _get_ttl(request.url.path))
                return

            cache_key = _build_cache_key(user_id)
            if await _replay_cached(cache_key):
                return

            await _run_with_lock(cache_key)

        except Exception:
            try:
                user_id = getattr(request.state, "user_id", None)
                if user_id:
                    cache_key = _build_cache_key(user_id)
                    await redis_client.delete(cache_key)
                await redis_client.delete(f"{cache_key}:lock")
            except Exception:
                pass
            await self.app(scope, receive, send)
