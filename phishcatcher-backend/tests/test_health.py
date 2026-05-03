"""
Tests for health check endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Root endpoint returns app info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PhishCatcher API"
    assert "api_version" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint returns database status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "databases" in data
    assert "api_version" in data


@pytest.mark.asyncio
async def test_health_ready_endpoint(client: AsyncClient):
    """Readiness endpoint checks database connections."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "databases" in data


@pytest.mark.asyncio
async def test_health_live_endpoint(client: AsyncClient):
    """Liveness endpoint returns alive status."""
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_api_version_header(client: AsyncClient):
    """All responses include X-API-Version header."""
    response = await client.get("/")
    assert "x-api-version" in response.headers
    assert response.headers["x-api-version"] == "v1"
