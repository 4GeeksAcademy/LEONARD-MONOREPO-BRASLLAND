import pytest
from fastapi import HTTPException

from services.api import auth


def test_current_account_includes_own_profile(database, user):
    auth.edit_profile(auth.ProfileUpdate(name="Owner", phone="123"), user, database)
    result = auth.auth_me(user, database)
    assert result["id"] == user.id
    assert result["profile"].user_id == user.id
    assert result["profile"].name == "Owner"
    assert "hashed_password" not in result


def test_empty_profile_is_valid_for_current_account(database, user):
    result = auth.auth_me(user, database)
    assert result["profile"].name == result["profile"].phone == result["profile"].address == ""


def test_read_profile_returns_own_profile(database, user):
    assert auth.read_profile(user, database).user_id == user.id
    assert auth.read_profile(user, database).name == ""


def test_profile_update_and_empty_update_preserve_other_fields(database, user):
    auth.edit_profile(auth.ProfileUpdate(name="Owner", phone="123"), user, database)
    profile = auth.edit_profile(auth.ProfileUpdate(address="New address"), user, database)
    assert (profile.name, profile.phone, profile.address) == ("Owner", "123", "New address")
    assert auth.edit_profile(auth.ProfileUpdate(), user, database) == profile


@pytest.mark.parametrize("endpoint", ["me", "read", "edit"])
def test_missing_profile_is_rejected(database, user, endpoint):
    database.table("profiles").truncate()
    with pytest.raises(HTTPException, match="Profile not found"):
        if endpoint == "me":
            auth.auth_me(user, database)
        elif endpoint == "read":
            auth.read_profile(user, database)
        else:
            auth.edit_profile(auth.ProfileUpdate(name="Owner"), user, database)