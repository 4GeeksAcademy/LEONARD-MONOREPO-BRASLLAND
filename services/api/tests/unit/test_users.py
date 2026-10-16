import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from services.api import auth


def test_admin_can_list_accounts_and_empty_database(database, user):
    admin = user.model_copy(update={"role": auth.Role.admin})
    assert [record["id"] for record in auth.list_users(admin, database)] == [user.id]
    auth.delete_user(database, user.id)
    assert auth.list_users(admin, database) == []


def test_non_admin_cannot_list_accounts(database, user):
    with pytest.raises(HTTPException, match="Only admins may list users"):
        auth.list_users(user, database)


@pytest.mark.parametrize("admin", [False, True])
def test_owner_or_admin_reads_account(database, user, admin):
    current = user.model_copy(update={"id": "admin-id", "role": auth.Role.admin}) if admin else user
    assert auth.read_user(user.id, current, database).id == user.id


@pytest.mark.parametrize("operation", ["read", "edit", "remove"])
def test_non_owner_cannot_access_account(database, user, operation):
    with pytest.raises(HTTPException, match="only access your own"):
        if operation == "read":
            auth.read_user("another-user", user, database)
        elif operation == "edit":
            auth.edit_user("another-user", auth.UserUpdate(email="new@example.com"), user, database)
        else:
            auth.remove_user("another-user", user, database)
    assert auth.find_user(database, user.id).email == user.email


@pytest.mark.parametrize("operation", ["read", "edit", "remove"])
def test_missing_account_is_rejected(database, user, operation):
    admin = user.model_copy(update={"role": auth.Role.admin})
    with pytest.raises(HTTPException, match="User not found"):
        if operation == "read":
            auth.read_user("missing", admin, database)
        elif operation == "edit":
            auth.edit_user("missing", auth.UserUpdate(), admin, database)
        else:
            auth.remove_user("missing", admin, database)


def test_owner_updates_email_and_password(database, user):
    updated = auth.edit_user(user.id, auth.UserUpdate(
        email="CHANGED@example.com", password="Replacement-password",
    ), user, database)
    assert updated.email == "changed@example.com"
    assert auth.bcrypt.verify("Replacement-password", updated.hashed_password)
    assert "password" not in database.table("users").all()[0]


def test_empty_update_preserves_account(database, user):
    assert auth.edit_user(user.id, auth.UserUpdate(), user, database) == user


@pytest.mark.parametrize("changes", [{"role": "admin"}, {"is_active": False}])
def test_owner_cannot_escalate_or_change_activation(database, user, changes):
    with pytest.raises(HTTPException, match="Only admins may change"):
        auth.edit_user(user.id, auth.UserUpdate(**changes), user, database)
    assert auth.find_user(database, user.id) == user


def test_admin_can_change_role_and_activation(database, user):
    admin = user.model_copy(update={"role": auth.Role.admin})
    updated = auth.edit_user(user.id, auth.UserUpdate(role="manager", is_active=False), admin, database)
    assert updated.role == auth.Role.manager
    assert not updated.is_active


def test_update_rejects_duplicate_email(database, user):
    auth.register(auth.UserCreate(email="other@example.com", password="Other-password"), database)
    with pytest.raises(HTTPException, match="Email is already registered"):
        auth.edit_user(user.id, auth.UserUpdate(email="OTHER@example.com"), user, database)
    assert auth.find_user(database, user.id).email == user.email


@pytest.mark.parametrize("field", ["email", "password", "role", "is_active"])
def test_explicit_null_update_is_not_an_empty_update(field):
    with pytest.raises(ValidationError):
        auth.UserUpdate(**{field: None})


@pytest.mark.parametrize("admin", [False, True])
def test_owner_or_admin_deletes_account_and_profile(database, user, admin):
    current = user.model_copy(update={"id": "admin-id", "role": auth.Role.admin}) if admin else user
    auth.remove_user(user.id, current, database)
    assert len(database.table("users")) == len(database.table("profiles")) == 0