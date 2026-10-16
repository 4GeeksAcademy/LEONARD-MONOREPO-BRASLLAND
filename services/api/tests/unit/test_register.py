import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from tinydb import Query

from services.api import auth


def test_register_creates_hashed_credentials_and_linked_profile(database):
    user = auth.register(auth.UserCreate(
        email="NEW@example.com", password="Correct-password-123", name="New Owner",
    ), database)
    assert user.email == "new@example.com"
    assert user.role == auth.Role.user
    assert user.is_active
    assert user.created_at.tzinfo is not None
    assert user.hashed_password != "Correct-password-123"
    assert auth.bcrypt.verify("Correct-password-123", user.hashed_password)
    assert auth.find_profile(database, user.id).name == "New Owner"


def test_duplicate_email_ignores_case_without_creating_extra_records(database, user):
    with pytest.raises(HTTPException, match="Email is already registered"):
        auth.register(auth.UserCreate(email="OWNER@example.com", password="Other-password"), database)
    assert len(database.table("users")) == len(database.table("profiles")) == 1


@pytest.mark.parametrize("changes", [
    {"password": ""}, {"password": "short"}, {"password": "x" * 73},
    {"password": "\u00e9" * 37}, {"email": "invalid"}, {"role": "admin"},
])
def test_registration_rejects_invalid_credentials_or_privilege(changes):
    with pytest.raises(ValidationError):
        auth.UserCreate(**({"email": "new@example.com", "password": "Valid-password"} | changes))


@pytest.mark.parametrize("password", ["x" * 8, "x" * 72, "\u00e9" * 36])
def test_password_accepts_exact_boundaries(password):
    assert auth.PasswordFields(password=password).password == password


def test_profile_storage_failure_rolls_back_user(database, monkeypatch):
    def fail_insert(record):
        raise OSError("storage unavailable")

    monkeypatch.setattr(database.table("profiles"), "insert", fail_insert)
    with pytest.raises(OSError, match="storage unavailable"):
        auth.register(auth.UserCreate(email="new@example.com", password="Valid-password"), database)
    assert not database.table("users").contains(Query().email == "new@example.com")
    assert len(database.table("profiles")) == 0