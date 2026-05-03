"""
Tests for security services.
"""

import pytest
from app.services.security import (
    validate_password_strength,
    get_password_hash,
    verify_password,
)
from app.schemas.auth import validate_password_strength as schema_validate


@pytest.mark.asyncio
class TestPasswordValidation:
    """Tests for password strength validation."""

    def test_strong_password_passes(self):
        valid, err = validate_password_strength("Str0ng!Pass#2024")
        assert valid is True
        assert err is None

    def test_too_short_fails(self):
        valid, err = validate_password_strength("Sh0rt!1")
        assert valid is False
        assert "12 characters" in err

    def test_no_uppercase_fails(self):
        valid, err = validate_password_strength("nouppercase1!")
        assert valid is False
        assert "uppercase" in err.lower()

    def test_no_lowercase_fails(self):
        valid, err = validate_password_strength("NOLOWERCASE1!")
        assert valid is False
        assert "lowercase" in err.lower()

    def test_no_digit_fails(self):
        valid, err = validate_password_strength("NoNumbersOrSpecial!")
        assert valid is False
        assert "number" in err.lower()

    def test_no_special_char_fails(self):
        valid, err = validate_password_strength("MissingSpecial1charA")
        assert valid is False
        assert "special" in err.lower()

    def test_empty_password_fails(self):
        valid, err = validate_password_strength("")
        assert valid is False


class TestSchemaPasswordValidator:
    """Tests for Pydantic schema password validation."""

    def test_strong_password_returns_value(self):
        result = schema_validate("Str0ng!Pass#2024")
        assert result == "Str0ng!Pass#2024"

    def test_weak_password_raises(self):
        with pytest.raises(ValueError, match="12 characters"):
            schema_validate("short")

    def test_no_uppercase_raises(self):
        with pytest.raises(ValueError, match="uppercase"):
            schema_validate("nouppercase1!abc")


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_is_not_plaintext(self):
        hashed = get_password_hash("TestP@ssw0rd!23")
        assert hashed != "TestP@ssw0rd!23"
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        hashed = get_password_hash("TestP@ssw0rd!23")
        assert verify_password("TestP@ssw0rd!23", hashed) is True

    def test_verify_wrong_password(self):
        hashed = get_password_hash("TestP@ssw0rd!23")
        assert verify_password("WrongP@ssw0rd!23", hashed) is False

    def test_unique_hashes(self):
        h1 = get_password_hash("SameP@ssw0rd!23")
        h2 = get_password_hash("SameP@ssw0rd!23")
        # bcrypt includes random salt, so hashes should differ
        assert h1 != h2
