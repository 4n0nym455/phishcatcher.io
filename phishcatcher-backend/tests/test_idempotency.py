"""
Tests for IdempotencyMiddleware.

Tests the middleware in isolation using a minimal ASGI app.
Uses mock Redis to avoid async event loop issues in tests.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware.idempotency_middleware import (
    IdempotencyMiddleware,
    _get_ttl,
    _strip_api_prefix,
    IDEMPOTENCY_KEY_HEADER,
    IDEMPOTENCY_RESPONSE_HEADER,
    TTL_BY_PATH,
    DEFAULT_TTL,
)


async def simple_endpoint(request):
    """Minimal endpoint that returns method and path."""
    return JSONResponse({"status": "ok", "method": request.method})


async def failing_endpoint(request):
    """Endpoint that returns error."""
    return JSONResponse({"error": "not found"}, status_code=404)


def create_test_app():
    """Create a minimal test app with idempotency middleware."""
    app = Starlette(
        routes=[
            Route("/api/v1/echo", simple_endpoint, methods=["POST", "GET", "PUT", "PATCH"]),
            Route("/api/v1/auth/register", simple_endpoint, methods=["POST"]),
            Route("/api/v1/auth/login", simple_endpoint, methods=["POST"]),
            Route("/api/v1/error", failing_endpoint, methods=["POST"]),
        ]
    )
    app.add_middleware(IdempotencyMiddleware)
    return app


@pytest.fixture
def mock_redis():
    """Create a mock Redis client that simulates Redis behavior."""
    store = {}

    class MockRedis:
        async def get(self, key):
            return store.get(key)

        async def set(self, key, value, **kwargs):
            store[key] = value
            return True

        async def setex(self, key, ttl, value):
            store[key] = value
            return True

        async def delete(self, key):
            store.pop(key, None)
            return 1

        async def keys(self, pattern):
            import fnmatch
            return [k for k in store.keys() if fnmatch.fnmatch(k, pattern)]

        async def ping(self):
            return True

    return MockRedis()


@pytest.fixture
def client(mock_redis):
    """Create test client with mocked Redis."""
    with patch("app.middleware.idempotency_middleware.get_redis_client", return_value=mock_redis):
        app = create_test_app()
        with TestClient(app) as c:
            yield c


class TestIdempotencyHelpers:

    def test_strip_api_prefix_v1(self):
        assert _strip_api_prefix("/api/v1/auth/register") == "/auth/register"

    def test_strip_api_prefix_no_prefix(self):
        assert _strip_api_prefix("/auth/register") == "/auth/register"

    def test_strip_api_prefix_v2(self):
        assert _strip_api_prefix("/api/v2/auth/register") == "/auth/register"

    def test_get_ttl_register(self):
        assert _get_ttl("/api/v1/auth/register") == 86400

    def test_get_ttl_login(self):
        assert _get_ttl("/api/v1/auth/login") == 600

    def test_get_ttl_gmail(self):
        assert _get_ttl("/api/v1/gmail/emails/queue") == 300

    def test_get_ttl_default(self):
        assert _get_ttl("/api/v1/unknown") == 3600

    def test_ttl_values_consistent(self):
        assert TTL_BY_PATH["/auth/register"] == 86400
        assert TTL_BY_PATH["/auth/login"] == 600
        assert TTL_BY_PATH["/gmail/"] == 300
        assert DEFAULT_TTL == 3600


class TestIdempotencyMiddleware:

    def test_get_bypasses_idempotency(self, client):
        """GET requests should never be cached."""
        resp = client.get("/api/v1/echo", headers={IDEMPOTENCY_KEY_HEADER: "key-1"})
        assert IDEMPOTENCY_RESPONSE_HEADER not in resp.headers

    def test_post_without_key_passes_through(self, client):
        """POST without idempotency key should not be cached."""
        resp = client.post("/api/v1/echo", json={"test": "data"})
        assert IDEMPOTENCY_RESPONSE_HEADER not in resp.headers

    def test_duplicate_post_returns_cached(self, client):
        """Two identical POSTs with same key should return cached response."""
        key = "test-dup-1"
        resp1 = client.post(
            "/api/v1/echo",
            json={"test": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: key},
        )
        resp2 = client.post(
            "/api/v1/echo",
            json={"test": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: key},
        )

        assert resp1.status_code == resp2.status_code
        assert resp1.json() == resp2.json()
        assert resp2.headers.get(IDEMPOTENCY_RESPONSE_HEADER) == "true"

    def test_different_keys_independent(self, client):
        """Different keys should produce independent responses."""
        resp1 = client.post(
            "/api/v1/echo",
            json={"test": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: "key-a"},
        )
        resp2 = client.post(
            "/api/v1/echo",
            json={"test": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: "key-b"},
        )

        assert resp1.status_code == resp2.status_code
        assert resp1.json() == resp2.json()
        assert resp1.headers.get(IDEMPOTENCY_RESPONSE_HEADER) == "true"
        assert resp2.headers.get(IDEMPOTENCY_RESPONSE_HEADER) == "true"

        resp3 = client.post(
            "/api/v1/echo",
            json={"test": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: "key-a"},
        )
        assert resp3.json() == resp1.json()

    def test_error_responses_cached(self, client):
        """Error responses should also be cached."""
        key = "test-error-1"
        resp1 = client.post(
            "/api/v1/error",
            json={"test": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: key},
        )
        resp2 = client.post(
            "/api/v1/error",
            json={"test": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: key},
        )

        assert resp1.status_code == resp2.status_code == 404
        assert resp1.json() == resp2.json()
        assert resp2.headers.get(IDEMPOTENCY_RESPONSE_HEADER) == "true"

    def test_put_request_idempotency(self, client):
        """PUT requests should support idempotency."""
        key = "test-put-1"
        resp1 = client.put(
            "/api/v1/echo",
            json={"update": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: key},
        )
        resp2 = client.put(
            "/api/v1/echo",
            json={"update": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: key},
        )

        assert resp1.status_code == resp2.status_code
        assert resp2.headers.get(IDEMPOTENCY_RESPONSE_HEADER) == "true"

    def test_patch_request_idempotency(self, client):
        """PATCH requests should support idempotency."""
        key = "test-patch-1"
        resp1 = client.patch(
            "/api/v1/echo",
            json={"patch": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: key},
        )
        resp2 = client.patch(
            "/api/v1/echo",
            json={"patch": "data"},
            headers={IDEMPOTENCY_KEY_HEADER: key},
        )

        assert resp1.status_code == resp2.status_code
        assert resp2.headers.get(IDEMPOTENCY_RESPONSE_HEADER) == "true"
