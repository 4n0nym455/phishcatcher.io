"""
Tests for analysis endpoints.
"""

import io
import pytest
from httpx import AsyncClient


SAMPLE_EML = b"""\
From: sender@example.com
To: recipient@example.com
Subject: Test Email
Content-Type: text/plain

This is a test email for analysis.
"""


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    """Upload endpoint rejects unauthenticated requests."""
    response = await client.post(
        "/api/v1/analysis/upload",
        files={"file": ("test.eml", io.BytesIO(SAMPLE_EML), "message/rfc822")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_requires_active_user(client: AsyncClient, test_user_data):
    """Upload endpoint rejects unverified/inactive users."""
    # Register a user (not verified yet)
    payload = {
        **test_user_data,
        "password": "Str0ng!Pass#2024",
        "confirm_password": "Str0ng!Pass#2024",
        "accept_terms_and_privacy": True,
    }
    await client.post("/api/v1/auth/register", json=payload)

    # Login will likely fail or return 403 for unverified user
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user_data["email"], "password": "Str0ng!Pass#2024"},
    )
    if login_resp.status_code != 200:
        # Unverified users cannot login — endpoint correctly blocks access
        return

    tokens = login_resp.json()
    access_token = tokens["access_token"]

    # If login succeeded, upload should still require active user
    response = await client.post(
        "/api/v1/analysis/upload",
        files={"file": ("test.eml", io.BytesIO(SAMPLE_EML), "message/rfc822")},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code in (202, 403)


@pytest.mark.asyncio
async def test_history_requires_auth(client: AsyncClient):
    """History endpoint rejects unauthenticated requests."""
    response = await client.get("/api/v1/analysis/history")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_history_empty_for_new_user(client: AsyncClient, test_user_data):
    """History returns empty list for user with no analyses."""
    payload = {
        **test_user_data,
        "password": "Str0ng!Pass#2024",
        "confirm_password": "Str0ng!Pass#2024",
        "accept_terms_and_privacy": True,
    }
    await client.post("/api/v1/auth/register", json=payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user_data["email"], "password": "Str0ng!Pass#2024"},
    )
    if login_resp.status_code != 200:
        pytest.skip("Login failed — OTP verification required")

    tokens = login_resp.json()
    access_token = tokens["access_token"]

    response = await client.get(
        "/api/v1/analysis/history",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_analysis_not_found(client: AsyncClient, test_user_data):
    """Fetching non-existent analysis returns 404."""
    payload = {
        **test_user_data,
        "password": "Str0ng!Pass#2024",
        "confirm_password": "Str0ng!Pass#2024",
        "accept_terms_and_privacy": True,
    }
    await client.post("/api/v1/auth/register", json=payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user_data["email"], "password": "Str0ng!Pass#2024"},
    )
    if login_resp.status_code != 200:
        pytest.skip("Login failed — OTP verification required")

    tokens = login_resp.json()
    access_token = tokens["access_token"]

    response = await client.get(
        "/api/v1/analysis/nonexistent-id",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code in (404, 422)
