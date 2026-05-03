"""
Test configuration and shared fixtures.

Provides async test client, database isolation, and mock users.
"""

import uuid
import asyncio
import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient

from app.main import app as application
import app.database
import app.core.session_manager as sm_mod

_SESSION_ID = str(uuid.uuid4())[:8]


def _reset_db_globals():
    """Reset all database clients so they are recreated on the active event loop."""
    import app.database as db
    import app.core.session_manager as sm
    import app.middleware.session_middleware as mw
    import app.routers.auth as auth

    db._engine = None
    db._async_session_maker = None
    sm._session_manager = None
    db._mongodb_client = None
    db._redis_client = None


@asynccontextmanager
async def _no_op_lifespan(app):
    """Bypass lifespan — databases initialized per-test as needed."""
    yield


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client. Resets DB clients per test for loop isolation."""
    _reset_db_globals()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        # Clean up: dispose engine to close all connections
        import app.database as db
        if db._engine:
            await db._engine.dispose()
            db._engine = None


@pytest.fixture
def test_user_data():
    """Return sample user registration data with unique email per test."""
    uid = str(uuid.uuid4())[:8]
    return {
        "email": f"test-{uid}@phishcatcher.io",
        "password": "TestP@ssw0rd!23",
        "full_name": "Test User",
    }


@pytest.fixture
def admin_user_data():
    """Return sample admin registration data with unique email per test."""
    uid = str(uuid.uuid4())[:8]
    return {
        "email": f"admin-test-{uid}@phishcatcher.io",
        "password": "AdminP@ssw0rd!23",
        "full_name": "Admin Tester",
    }


@pytest.fixture
def valid_passwords():
    """Return list of passwords that should pass validation."""
    return [
        "Str0ng!Pass#2024",
        "SecureP@ssw0rd99",
        "C0mpl3x!Passw0rd",
    ]


@pytest.fixture
def invalid_passwords():
    """Return list of passwords that should fail validation."""
    return [
        "short",
        "nouppercase1!",
        "NOLOWERCASE1!",
        "NoNumbersOrSpecial",
        "MissingSpecial1char",
    ]


@pytest.fixture(autouse=True)
def mock_brevo(monkeypatch):
    """Mock Brevo email service to prevent real emails during tests."""
    import app.services.brevo_service as brevo_mod

    class MockBrevoService:
        def __init__(self):
            self.api_key = None
            self.from_email = "test@phishcatcher.io"
            self.from_name = "PhishCatcher"
            self.sent_emails = []

        async def send_email(self, to_email, subject, html_content):
            self.sent_emails.append({"to": to_email, "subject": subject})
            return True

        async def send_verification_code(self, to_email, code, action):
            self.sent_emails.append({"to": to_email, "code": code})
            return True

        def _build_email(self, **kwargs):
            return "<html>mock</html>"

    mock_instance = MockBrevoService()
    monkeypatch.setattr(brevo_mod, "brevo_service", mock_instance)
    return mock_instance


@pytest.fixture(autouse=True)
def mock_sms(monkeypatch):
    """Mock SMS service to prevent real SMS during tests."""
    import app.services.sms_service as sms_mod

    class MockSmsService:
        def __init__(self):
            self.api_key = None
            self.sender = "PhishCatch"
            self.sent_messages = []

        async def send_sms(self, to_phone, content, **kwargs):
            self.sent_messages.append({"to": to_phone, "content": content})
            return True

        async def send_otp(self, to_phone, code):
            self.sent_messages.append({"to": to_phone, "code": code, "type": "otp"})
            return True

        async def send_password_reset_sms(self, to_phone, code):
            self.sent_messages.append({"to": to_phone, "code": code, "type": "password_reset"})
            return True

    mock_instance = MockSmsService()
    monkeypatch.setattr(sms_mod, "sms_service", mock_instance)
    return mock_instance
