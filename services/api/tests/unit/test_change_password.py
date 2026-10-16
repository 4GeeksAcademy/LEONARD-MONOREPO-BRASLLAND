import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from services.api import auth


@pytest.mark.parametrize("new_password", ["Replacement-password", "Correct-password-123"])
def test_change_password_updates_hash_and_invalidates_reset_links(database, user, new_password):
    database.table("password_reset_tokens").insert({"user_id": user.id, "id": "old-link"})
    database.table("password_reset_tokens").insert({"user_id": "other-user", "id": "keep-link"})
    auth.change_password(auth.ChangePasswordRequest(
        current_password="Correct-password-123", new_password=new_password,
    ), user, database)
    assert auth.bcrypt.verify(new_password, auth.find_user(database, user.id).hashed_password)
    assert [record["id"] for record in database.table("password_reset_tokens").all()] == ["keep-link"]


def test_incorrect_current_password_leaves_credentials_and_reset_links_unchanged(database, user):
    database.table("password_reset_tokens").insert({"user_id": user.id, "id": "old-link"})
    with pytest.raises(HTTPException, match="Current password is incorrect"):
        auth.change_password(auth.ChangePasswordRequest(
            current_password="Wrong-password", new_password="Replacement-password",
        ), user, database)
    assert auth.find_user(database, user.id).hashed_password == user.hashed_password
    assert len(database.table("password_reset_tokens")) == 1


@pytest.mark.parametrize("changes", [{"current_password": ""}, {"new_password": ""}, {"current_password": "\u00e9" * 37}])
def test_change_password_rejects_boundary_inputs(changes):
    with pytest.raises(ValidationError):
        auth.ChangePasswordRequest(**({"current_password": "Correct-password-123", "new_password": "Replacement-password"} | changes))