from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tinydb import TinyDB
from tinydb.storages import MemoryStorage

from services.api import auth


@pytest.fixture
def database():
    with TinyDB(storage=MemoryStorage) as database:
        yield database


@pytest.fixture
def user(database):
    return auth.register(
        auth.UserCreate(email="owner@example.com", password="Correct-password-123"),
        database,
    )


@pytest.fixture
def auth_request():
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        jwt_secret="unit-test-secret-not-for-production-123456",
        token_expiry=30,
        password_reset_expiry=30,
    )))


@pytest.fixture
def login_request(auth_request):
    def build(payload, form=False):
        return SimpleNamespace(
            app=auth_request.app,
            headers={"content-type": "application/x-www-form-urlencoded" if form else "application/json"},
            json=AsyncMock(return_value=payload),
            form=AsyncMock(return_value=payload),
        )
    return build