"""Grow the dataset so latency measurements resemble production.

Usage: python scripts/seed_load_data.py [--incidents 20000] [--ingredients 400] [--movements 150000] [--seed 7]
Writes incidents to the TinyDB file (SUPPLIERS_DB_PATH) and inventory rows to the
database configured through SUPABASE_DATABASE_URL / SUPABASE_DB_*. Re-running adds more rows.
"""
import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from shared.incidents import (
    INCIDENT_BRANCHES, INCIDENT_CATEGORIES, INCIDENT_ORIGINS, INCIDENT_STATUSES,
)
from services.api.app.database import engine
from services.api.app.models import Ingredient, IngredientEntry, IngredientExit, LOCATION_IDS
from services.api.database import open_database
from sqlmodel import Session, SQLModel

INGREDIENTS = {
    "carne": ["Beef sirloin", "Pork ribs", "Chicken thigh", "Chorizo", "Skirt steak", "Short ribs"],
    "verduras_y_hortalizas": ["Tomato", "Red onion", "Avocado", "Plantain", "Cilantro", "Lime"],
    "salsas_y_condimentos": ["Chimichurri", "Hot sauce", "Garlic paste", "Aji", "Cumin", "Sea salt"],
    "bebidas": ["Lemonade", "Cola", "Sparkling water", "Lulo juice", "Craft lager", "Coffee beans"],
    "packaging": ["Takeaway box", "Paper bag", "Napkins", "Cutlery set", "Foil tray", "Sauce cup"],
    "productos_limpieza": ["Degreaser", "Sanitiser", "Floor cleaner", "Gloves", "Sponges", "Bin liners"],
    "lacteos": ["Queso fresco", "Butter", "Cream", "Milk", "Arequipe", "Mozzarella"],
    "carbon_y_combustible": ["Charcoal", "Hardwood chunks", "Gas canister", "Firelighters", "Pellets", "Briquettes"],
}
UNITS = {"carne": "kg", "verduras_y_hortalizas": "kg", "bebidas": "l", "lacteos": "kg", "carbon_y_combustible": "kg"}
ISSUES = [
    "Walk-in fridge temperature alarm", "Late delivery from supplier", "Customer reported undercooked order",
    "Grill ignition failure", "Staff shortage on weekend shift", "Wrong packaging received",
    "Delivery driver damaged crates", "Customer complaint about wait time", "POS terminal offline",
]


def seed_incidents(count: int, rng: random.Random) -> None:
    now = datetime.now(timezone.utc)
    records = []
    for _ in range(count):
        created = now - timedelta(minutes=rng.randint(0, 60 * 24 * 365))
        text = f"{rng.choice(ISSUES)} ({rng.choice(INCIDENT_BRANCHES)})"
        records.append({
            "title": text[:160], "description": text + ". Logged during automated load seeding.",
            "category": rng.choice(INCIDENT_CATEGORIES),
            "status": rng.choices(INCIDENT_STATUSES, weights=(30, 25, 40, 5))[0],
            "origin": rng.choices(INCIDENT_ORIGINS, weights=(50, 35, 15))[0],
            "branch": rng.choice(INCIDENT_BRANCHES),
            "created_at": created.isoformat(), "updated_at": created.isoformat(),
        })
    with open_database() as database:
        database.table("incidents").insert_multiple(records)
        print(f"incidents: +{count}, total {len(database.table('incidents'))}")


def seed_inventory(ingredient_count: int, movement_count: int, rng: random.Random) -> None:
    if engine is None:
        print("inventory: skipped, no database configured")
        return
    SQLModel.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        base = session.query(Ingredient).count()
        for index in range(ingredient_count):
            category = rng.choice(list(INGREDIENTS))
            session.add(Ingredient(
                name=f"{rng.choice(INGREDIENTS[category])} {rng.choice(['A', 'B', 'Premium', 'Bulk', 'Local'])}",
                sku=f"{category[:3].upper()}-{base + index:06d}", category=category,
                unit=UNITS.get(category, "unit"),
            ))
        session.commit()
        ids = [row for (row,) in session.query(Ingredient.id).all()]
        for number in range(movement_count):
            outbound = number % 3 == 0
            model = IngredientExit if outbound else IngredientEntry
            session.add(model(
                ingredient_id=rng.choice(ids), location_id=rng.choice(LOCATION_IDS),
                quantity=Decimal(rng.randint(1, 400)) / 4 * (1 if outbound else 3),
                created_at=now - timedelta(minutes=rng.randint(0, 60 * 24 * 365)),
                user_uuid="00000000-0000-4000-8000-000000000000",
            ))
            if number % 5000 == 4999:
                session.commit()
        session.commit()
        print(f"inventory: ingredients {len(ids)}, movements +{movement_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--incidents", type=int, default=20000)
    parser.add_argument("--ingredients", type=int, default=400)
    parser.add_argument("--movements", type=int, default=150000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    generator = random.Random(args.seed)
    seed_incidents(args.incidents, generator)
    seed_inventory(args.ingredients, args.movements, generator)
