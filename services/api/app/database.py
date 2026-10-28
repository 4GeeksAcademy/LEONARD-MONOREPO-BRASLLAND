import os
from collections.abc import Iterator
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.engine import Engine, URL
from sqlmodel import Session, create_engine


ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def get_inventory_database_url() -> str | URL | None:
    database_url = os.environ.get("SUPABASE_DATABASE_URL")
    if database_url:
        return database_url

    host = os.environ.get("SUPABASE_DB_HOST")
    port = os.environ.get("SUPABASE_DB_PORT")
    database = os.environ.get("SUPABASE_DB_NAME") or os.environ.get("SUPABASE_DB_DATABASE")
    username = os.environ.get("SUPABASE_DB_USER")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not all((host, port, database, username, password)):
        return None
    try:
        port_number = int(port)
    except ValueError as error:
        raise RuntimeError("SUPABASE_DB_PORT must be a valid port number.") from error
    return URL.create(
        "postgresql+psycopg",
        username=username,
        password=password,
        host=host,
        port=port_number,
        database=database,
        query={"sslmode": "require"},
    )


def create_inventory_engine(database_url: str | URL | None) -> Engine | None:
    if not database_url:
        return None
    if isinstance(database_url, str) and database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif isinstance(database_url, str) and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )


engine = create_inventory_engine(get_inventory_database_url())


def get_db() -> Iterator[Session]:
    if engine is None:
        raise HTTPException(
            503,
            "Inventory database is not configured. Set SUPABASE_DATABASE_URL or complete SUPABASE_DB_* settings.",
        )
    with Session(engine) as session:
        yield session