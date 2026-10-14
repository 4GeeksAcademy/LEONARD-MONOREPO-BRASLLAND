import hashlib
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from fastapi.testclient import TestClient
from tinydb import Query

from services.api.app.main import app


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            "AUTH_DB_PATH": str(Path(self.directory.name) / "auth.json"),
            "SUPPLIERS_DB_PATH": str(Path(self.directory.name) / "suppliers.json"),
            "JWT_SECRET_KEY": "test-password-reset-secret-" * 3,
            "RESEND_API_KEY": "re_test_key",
            "RESEND_FROM_EMAIL": "Brasaland <onboarding@resend.dev>",
            "FRONTEND_BASE_URL": "http://localhost:3001",
        })
        self.environment.start()
        self.client = TestClient(app)
        self.client.__enter__()
        self.email = "password-reset@example.com"
        self.password = "Current-test-password"
        response = self.client.post("/users", json={"email": self.email, "password": self.password})
        self.assertEqual(response.status_code, 201, response.text)
        self.user_id = response.json()["id"]
        response = self.client.post("/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        self.access_token = response.json()["access_token"]

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.environment.stop()
        self.directory.cleanup()

    def request_reset_token(self, email_send):
        response = self.client.post("/auth/forgot-password", json={"email": self.email})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "message": "If that address is registered, you'll receive a reset link shortly."
        })
        email_payload = email_send.call_args.kwargs["json"]
        self.assertEqual(email_payload["to"], [self.email])
        self.assertIn("/reset-password?token=", email_payload["text"])
        reset_url = next(word for word in email_payload["text"].split() if "reset-password?token=" in word)
        return parse_qs(urlsplit(reset_url).query)["token"][0]

    @patch("services.api.auth.httpx.post")
    def test_forgot_password_is_generic_and_email_contains_hashed_one_use_token(self, send_email):
        response = self.client.post("/auth/forgot-password", json={"email": "unknown@example.com"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "message": "If that address is registered, you'll receive a reset link shortly."
        })
        send_email.assert_not_called()

        token = self.request_reset_token(send_email)
        send_email.assert_called_once()
        token_record = app.state.auth_db.table("password_reset_tokens").get(Query().user_id == self.user_id)
        self.assertIsNotNone(token_record)
        self.assertEqual(token_record["id"], hashlib.sha256(token.encode("utf-8")).hexdigest())
        self.assertNotIn(token, str(token_record))
        self.assertIn("This link expires", send_email.call_args.kwargs["json"]["html"])

        response = self.client.post("/auth/reset-password", json={"token": token, "new_password": "New-test-password"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["message"], "Password has been reset.")
        self.assertIsNone(app.state.auth_db.table("password_reset_tokens").get(Query().id == token_record["id"]))
        self.assertEqual(self.client.post("/auth/reset-password", json={"token": token, "new_password": "Another-password"}).status_code, 400)
        self.assertEqual(self.client.post("/auth/login", json={"email": self.email, "password": self.password}).status_code, 401)
        self.assertEqual(self.client.post("/auth/login", json={"email": self.email, "password": "New-test-password"}).status_code, 200)

    @patch("services.api.auth.httpx.post")
    def test_expired_and_unknown_reset_tokens_are_rejected(self, send_email):
        token = self.request_reset_token(send_email)
        tokens = app.state.auth_db.table("password_reset_tokens")
        tokens.update(
            {"expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()},
            Query().user_id == self.user_id,
        )
        response = self.client.post("/auth/reset-password", json={"token": token, "new_password": "New-test-password"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid or expired reset token.")
        self.assertIsNone(tokens.get(Query().user_id == self.user_id))
        response = self.client.post("/auth/reset-password", json={"token": "x" * 43, "new_password": "New-test-password"})
        self.assertEqual(response.status_code, 400)

    def test_change_password_requires_session_and_checks_current_password(self):
        payload = {"current_password": self.password, "new_password": "Changed-test-password"}
        self.assertEqual(self.client.post("/auth/change-password", json=payload).status_code, 401)
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = self.client.post("/auth/change-password", json={**payload, "current_password": "incorrect-password"}, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Current password is incorrect.")
        response = self.client.post("/auth/change-password", json=payload, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.post("/auth/login", json={"email": self.email, "password": self.password}).status_code, 401)
        self.assertEqual(self.client.post("/auth/login", json={"email": self.email, "password": "Changed-test-password"}).status_code, 200)


if __name__ == "__main__":
    unittest.main()