import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.database import get_db
from services.api.app.models import IngredientEntry
from services.api.auth import Role, User, get_current_user, require_authentication
from services.api.main import app


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            "JWT_SECRET_KEY": "test-secret-for-inventory-test-only-0123456789",
            "AUTH_DB_PATH": str(Path(self.directory.name) / "auth.json"),
            "SUPPLIERS_DB_PATH": str(Path(self.directory.name) / "suppliers.json"),
        })
        self.environment.start()
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        SQLModel.metadata.create_all(self.engine)
        self.user_id = str(uuid4())
        user = User(
            id=self.user_id,
            email="inventory@example.com",
            is_active=True,
            role=Role.user,
            created_at=datetime.now(timezone.utc),
            hashed_password="not-used-by-test",
        )
        app.dependency_overrides[get_db] = self.get_session
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[require_authentication] = lambda: user
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.environment.stop()
        self.directory.cleanup()

    def get_session(self):
        with Session(self.engine) as session:
            yield session

    def test_location_stock_and_order_audit(self):
        ingredient_response = self.client.post("/inventory/products", json={
            "name": "Ground beef",
            "sku": "ING-BEEF-001",
            "category": "carne",
            "unit": "kg",
        })
        self.assertEqual(ingredient_response.status_code, 201, ingredient_response.text)
        ingredient = ingredient_response.json()
        ingredient_id = ingredient["id"]
        self.assertEqual(ingredient["current_stock"], 0)
        self.assertEqual(self.client.post("/inventory/products", json={
            "name": "Direct stock edit",
            "sku": "ING-BEEF-002",
            "category": "carne",
            "unit": "kg",
            "current_stock": 100,
        }).status_code, 422)

        for location_id, quantity in (("COL-01", "10"), ("FLA-01", "3")):
            inbound = self.client.post("/inventory/orders/inbound", json={
                "ingredient_id": ingredient_id,
                "location_id": location_id,
                "quantity": quantity,
            })
            self.assertEqual(inbound.status_code, 201, inbound.text)
            self.assertEqual(inbound.json()["user_uuid"], self.user_id)

        outbound = self.client.post("/inventory/orders/outbound", json={
            "ingredient_id": ingredient_id,
            "location_id": "COL-01",
            "quantity": "8",
        })
        self.assertEqual(outbound.status_code, 201, outbound.text)
        self.assertEqual(outbound.json()["user_uuid"], self.user_id)
        self.assertEqual(self.client.get(
            f"/inventory/products/{ingredient_id}", params={"location_id": "COL-01"},
        ).json()["current_stock"], 2)
        self.assertEqual(self.client.get(
            f"/inventory/products/{ingredient_id}", params={"location_id": "FLA-01"},
        ).json()["current_stock"], 3)
        self.assertEqual(self.client.get(
            "/inventory/products", params={"location_id": "COL-01"},
        ).json()[0]["current_stock"], 2)

        rejected = self.client.post("/inventory/orders/outbound", json={
            "ingredient_id": ingredient_id,
            "location_id": "COL-01",
            "quantity": "3",
        })
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("Insufficient stock at COL-01", rejected.json()["detail"])

        orders = self.client.get("/inventory/orders").json()
        self.assertEqual(len(orders), 3)
        self.assertTrue(all(order["ingredient_name"] == "Ground beef" for order in orders))
        self.assertTrue(all(order["user_uuid"] == self.user_id for order in orders))

    def test_inventory_routes_require_authentication(self):
        app.dependency_overrides.pop(get_current_user)
        app.dependency_overrides.pop(require_authentication)
        self.assertEqual(self.client.get(
            "/inventory/products", params={"location_id": "COL-01"},
        ).status_code, 401)
        self.assertEqual(self.client.post("/inventory/products", json={
            "name": "Unauthorized ingredient",
            "sku": "ING-NOAUTH-001",
            "category": "carne",
            "unit": "kg",
        }).status_code, 401)

    def test_database_rejects_dangling_ingredient_foreign_key(self):
        with Session(self.engine) as session:
            session.add(IngredientEntry(
                ingredient_id=999,
                location_id="COL-01",
                quantity=1,
                user_uuid=str(uuid4()),
            ))
            with self.assertRaises(IntegrityError):
                session.commit()


if __name__ == "__main__":
    unittest.main()