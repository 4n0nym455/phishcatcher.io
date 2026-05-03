"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient


VALID_PASSWORD = "Str0ng!Pass#2024"


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, test_user_data):
    """Registration creates a new user and returns 201."""
    payload = {
        **test_user_data,
        "password": VALID_PASSWORD,
        "confirm_password": VALID_PASSWORD,
        "accept_terms_and_privacy": True,
    }
    response = await client.post(
        "/api/v1/auth/register",
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["full_name"] == test_user_data["full_name"]


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient, test_user_data):
    """Duplicate registration returns 400."""
    payload = {
        **test_user_data,
        "password": VALID_PASSWORD,
        "confirm_password": VALID_PASSWORD,
        "accept_terms_and_privacy": True,
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in (400, 409)


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Registration with invalid email returns 400 (email validation in router)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "accept_terms_and_privacy": True,
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Registration with weak password returns 422 (Pydantic validation)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@phishcatcher.io",
            "password": "short",
            "confirm_password": "short",
            "accept_terms_and_privacy": True,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_forgot_password_no_enumeration(client: AsyncClient):
    """Forgot password always returns 200 to prevent email enumeration."""
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@phishcatcher.io"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Login with invalid credentials returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nope@phishcatcher.io", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(client: AsyncClient):
    """Protected endpoints reject unauthenticated requests."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
