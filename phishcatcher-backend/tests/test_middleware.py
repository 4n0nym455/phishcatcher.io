"""
Tests for middleware components.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app as application


@pytest.mark.asyncio
async def test_api_version_header(client: AsyncClient):
    """Every response includes X-API-Version header."""
    response = await client.get("/health")
    assert "x-api-version" in response.headers
    assert response.headers["x-api-version"] == "v1"


@pytest.mark.asyncio
async def test_public_paths_not_rejected(client: AsyncClient):
    """Public endpoints return responses without auth."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "short",
            "confirm_password": "short",
            "accept_terms_and_privacy": True,
        },
    )
    # Should get a validation error, not 401
    assert response.status_code != 401


@pytest.mark.asyncio
async def test_protected_endpoint_returns_401_unauthenticated(client: AsyncClient):
    """Authenticated endpoint rejects requests without token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
