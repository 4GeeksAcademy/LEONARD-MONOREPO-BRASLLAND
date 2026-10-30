from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, Numeric
from sqlmodel import Field, Relationship, SQLModel


LOCATION_IDS = (
    "COL-01", "COL-02", "COL-03", "COL-04", "COL-05",
    "COL-06", "COL-07", "COL-08", "COL-09", "COL-10",
    "FLA-01", "FLA-02", "FLA-03", "FLA-04",
)
LOCATION_CHECK = "location_id IN (" + ", ".join(f"'{location}'" for location in LOCATION_IDS) + ")"


class Ingredient(SQLModel, table=True):
    __tablename__ = "ingredients"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=120, index=True)
    sku: str = Field(max_length=64, unique=True, index=True)
    category: str = Field(max_length=40)
    unit: str = Field(max_length=24)

    entries: list["IngredientEntry"] = Relationship(back_populates="ingredient")
    exits: list["IngredientExit"] = Relationship(back_populates="ingredient")


class IngredientEntry(SQLModel, table=True):
    __tablename__ = "ingredient_entries"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_ingredient_entries_positive_quantity"),
        CheckConstraint(LOCATION_CHECK, name="ck_ingredient_entries_location"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredients.id", index=True, ondelete="RESTRICT")
    location_id: str = Field(max_length=6, index=True)
    quantity: Decimal = Field(sa_column=Column(Numeric(14, 3), nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    user_uuid: str = Field(max_length=36, index=True)

    ingredient: Ingredient = Relationship(back_populates="entries")


class IngredientExit(SQLModel, table=True):
    __tablename__ = "ingredient_exits"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_ingredient_exits_positive_quantity"),
        CheckConstraint(LOCATION_CHECK, name="ck_ingredient_exits_location"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredients.id", index=True, ondelete="RESTRICT")
    location_id: str = Field(max_length=6, index=True)
    quantity: Decimal = Field(sa_column=Column(Numeric(14, 3), nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    user_uuid: str = Field(max_length=36, index=True)

    ingredient: Ingredient = Relationship(back_populates="exits")