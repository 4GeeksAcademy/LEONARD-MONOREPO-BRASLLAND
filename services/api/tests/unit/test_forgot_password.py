import hashlib

import pytest
from fastapi import BackgroundTasks

from services.api import auth


def test_reset_request_stores_only_digest_and_queues_delivery(database, user, auth_request):
    tasks = BackgroundTasks()
    auth.forgot_password(auth.ForgotPasswordRequest(email="OWNER@example.com"), tasks, auth_request, database)
    assert len(tasks.tasks) == 1
    delivery = tasks.tasks[0]
    assert delivery.func is auth.deliver_password_reset_email
    token = delivery.args[-1]
    record = database.table("password_reset_tokens").all()[0]
    assert record["id"] == hashlib.sha256(token.encode()).hexdigest()
    assert record["user_id"] == user.id
    assert token not in str(record)


def test_new_reset_request_replaces_previous_link(database, user, auth_request):
    tasks = BackgroundTasks()
    payload = auth.ForgotPasswordRequest(email=user.email)
    auth.forgot_password(payload, tasks, auth_request, database)
    previous = database.table("password_reset_tokens").all()[0]["id"]
    auth.forgot_password(payload, tasks, auth_request, database)
    records = database.table("password_reset_tokens").all()
    assert len(records) == 1
    assert records[0]["id"] != previous


def test_unknown_email_does_not_disclose_account_existence(database, user, auth_request):
    tasks = BackgroundTasks()
    unknown = auth.forgot_password(auth.ForgotPasswordRequest(email="unknown@example.com"), tasks, auth_request, database)
    assert not tasks.tasks
    assert len(database.table("password_reset_tokens")) == 0
    known = auth.forgot_password(auth.ForgotPasswordRequest(email=user.email), tasks, auth_request, database)
    assert known == unknown


def test_delivery_failure_removes_reset_link(database, user, auth_request, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "sender@example.com")

    def unavailable(*args, **kwargs):
        raise auth.httpx.ConnectError("offline")

    monkeypatch.setattr(auth.httpx, "post", unavailable)
    tasks = BackgroundTasks()
    auth.forgot_password(auth.ForgotPasswordRequest(email=user.email), tasks, auth_request, database)
    auth.deliver_password_reset_email(*tasks.tasks[0].args)
    assert len(database.table("password_reset_tokens")) == 0