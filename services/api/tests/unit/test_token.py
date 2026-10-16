from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt
from tinydb import Query

from services.api import auth


def test_expired_signed_token_is_rejected(auth_request, database, user):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": user.id, "user_id": user.id, "iat": now - timedelta(hours=1),
         "exp": now - timedelta(minutes=1)},
        auth_request.app.state.jwt_secret, algorithm="HS256",
    )
    with pytest.raises(HTTPException) as error:
        auth.get_current_user(auth_request, database, token)
    assert error.value.status_code == 401


@pytest.mark.parametrize("token", [None, "", "not-a-jwt", "a.b.c"])
def test_missing_or_malformed_token_is_rejected(auth_request, database, token):
    with pytest.raises(HTTPException, match="Invalid or missing access token"):
        auth.get_current_user(auth_request, database, token)


@pytest.mark.parametrize("change", [
    {"user_id": "someone-else"}, {"sub": 123}, {"sub": None},
    {"exp": None}, {"iat": None},
])
def test_invalid_identity_or_required_claim_is_rejected(auth_request, database, user, change):
    now = datetime.now(timezone.utc)
    claims = {"sub": user.id, "user_id": user.id, "iat": now, "exp": now + timedelta(minutes=5)}
    for key, value in change.items():
        if value is None:
            claims.pop(key)
        else:
            claims[key] = value
    token = jwt.encode(claims, auth_request.app.state.jwt_secret, algorithm="HS256")
    with pytest.raises(HTTPException, match="Invalid or missing access token"):
        auth.get_current_user(auth_request, database, token)


@pytest.mark.parametrize("state", ["valid", "inactive", "deleted", "wrong-secret"])
def test_token_checks_current_account_state(auth_request, database, user, state):
    now = datetime.now(timezone.utc)
    secret = "different-signing-secret" if state == "wrong-secret" else auth_request.app.state.jwt_secret
    token = jwt.encode({"sub": user.id, "user_id": user.id, "iat": now,
                        "exp": now + timedelta(minutes=5)}, secret, algorithm="HS256")
    if state == "inactive":
        database.table("users").update({"is_active": False}, Query().id == user.id)
    elif state == "deleted":
        auth.delete_user(database, user.id)
    if state == "valid":
        assert auth.get_current_user(auth_request, database, token).id == user.id
    else:
        with pytest.raises(HTTPException, match="Invalid or missing access token"):
            auth.get_current_user(auth_request, database, token)