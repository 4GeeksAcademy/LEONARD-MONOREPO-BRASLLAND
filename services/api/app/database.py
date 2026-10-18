import os
from collections.abc import Iterator
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine


ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def create_inventory_engine(database_url: str | None) -> Engine | None:
    if not database_url:
        return None
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return create_engine(database_url, pool_pre_ping=True)


engine = create_inventory_engine(os.environ.get("SUPABASE_DATABASE_URL"))


def get_db() -> Iterator[Session]:
    if engine is None:
        raise HTTPException(503, "Inventory database is not configured. Set SUPABASE_DATABASE_URL.")
    with Session(engine) as session:
        yield session