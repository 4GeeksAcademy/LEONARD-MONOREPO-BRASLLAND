import asyncio
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from jose import jwt
from tinydb import Query

from services.api import auth


@pytest.mark.parametrize("form", [False, True])
def test_login_issues_signed_identity_and_configured_expiry(database, user, login_request, form):
    payload = {"username" if form else "email": "OWNER@example.com", "password": "Correct-password-123"}
    request = login_request(payload, form=form)
    token = asyncio.run(auth.login(request, database))
    claims = jwt.decode(token.access_token, request.app.state.jwt_secret, algorithms=["HS256"])
    assert claims["sub"] == claims["user_id"] == user.id
    assert claims["exp"] - claims["iat"] == 30 * 60
    assert claims["exp"] > datetime.now(timezone.utc).timestamp()
    assert auth.get_current_user(request, database, token.access_token).id == user.id


@pytest.mark.parametrize("password", ["", "wrong-password", "x" * 73, "\u00e9" * 37])
def test_invalid_password_is_rejected(database, user, login_request, password):
    with pytest.raises(HTTPException, match="Invalid or missing access token"):
        asyncio.run(auth.login(login_request({"email": user.email, "password": password}), database))


def test_unknown_account_is_rejected(database, login_request):
    with pytest.raises(HTTPException, match="Invalid or missing access token"):
        asyncio.run(auth.login(login_request({"email": "absent@example.com", "password": "Valid-password"}), database))


def test_inactive_account_is_rejected(database, user, login_request):
    database.table("users").update({"is_active": False}, Query().id == user.id)
    with pytest.raises(HTTPException, match="Invalid or missing access token"):
        asyncio.run(auth.login(login_request({"email": user.email, "password": "Correct-password-123"}), database))


@pytest.mark.parametrize("payload", [[], {}, {"email": 123, "password": "Valid-password"}, {"email": "owner@example.com"}])
def test_missing_or_wrong_type_credentials_are_rejected(database, login_request, payload):
    with pytest.raises(HTTPException, match="Provide email and password"):
        asyncio.run(auth.login(login_request(payload), database))