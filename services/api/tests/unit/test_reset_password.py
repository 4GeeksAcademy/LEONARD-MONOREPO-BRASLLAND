from datetime import datetime, timedelta, timezone

import pytest
from fastapi import BackgroundTasks, HTTPException
from pydantic import ValidationError

from services.api import auth


@pytest.fixture
def reset_payload(database, user, auth_request):
    tasks = BackgroundTasks()
    auth.forgot_password(auth.ForgotPasswordRequest(email=user.email), tasks, auth_request, database)
    return auth.ResetPasswordRequest(token=tasks.tasks[0].args[-1], new_password="Replacement-password")


def test_reset_changes_credentials_and_consumes_token(database, user, reset_payload):
    auth.reset_password(reset_payload, database)
    updated = auth.find_user(database, user.id)
    assert auth.bcrypt.verify(reset_payload.new_password, updated.hashed_password)
    assert not auth.bcrypt.verify("Correct-password-123", updated.hashed_password)
    assert len(database.table("password_reset_tokens")) == 0
    with pytest.raises(HTTPException, match="Invalid or expired reset token"):
        auth.reset_password(reset_payload, database)


@pytest.mark.parametrize("expiry", ["expired", "invalid", None])
def test_expired_or_corrupt_expiry_does_not_change_password(database, user, reset_payload, expiry):
    value = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat() if expiry == "expired" else expiry
    database.table("password_reset_tokens").update({"expires_at": value})
    with pytest.raises(HTTPException, match="Invalid or expired reset token"):
        auth.reset_password(reset_payload, database)
    assert auth.find_user(database, user.id).hashed_password == user.hashed_password
    assert len(database.table("password_reset_tokens")) == 0


def test_unknown_reset_token_is_rejected(database):
    with pytest.raises(HTTPException, match="Invalid or expired reset token"):
        auth.reset_password(auth.ResetPasswordRequest(token="x" * 43, new_password="Replacement-password"), database)


def test_deleted_account_cannot_be_reset(database, user, reset_payload):
    auth.delete_user(database, user.id)
    with pytest.raises(HTTPException, match="Invalid or expired reset token"):
        auth.reset_password(reset_payload, database)
    assert len(database.table("password_reset_tokens")) == 0


@pytest.mark.parametrize("password", ["", "\u00e9" * 37])
def test_reset_password_rejects_invalid_password(password):
    with pytest.raises(ValidationError):
        auth.ResetPasswordRequest(token="x" * 43, new_password=password)