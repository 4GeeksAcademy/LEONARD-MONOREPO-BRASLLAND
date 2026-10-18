from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


IngredientCategory = Literal[
    "carne", "verduras_y_hortalizas", "salsas_y_condimentos", "bebidas",
    "packaging", "productos_limpieza", "lacteos", "carbon_y_combustible",
]
LocationId = Literal[
    "COL-01", "COL-02", "COL-03", "COL-04", "COL-05",
    "COL-06", "COL-07", "COL-08", "COL-09", "COL-10",
    "FLA-01", "FLA-02", "FLA-03", "FLA-04",
]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]


class IngredientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    sku: str = Field(min_length=1, max_length=64)
    category: IngredientCategory
    unit: str = Field(min_length=1, max_length=24)


class IngredientRead(IngredientCreate):
    id: int
    current_stock: float


class IngredientEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_id: int = Field(gt=0)
    location_id: LocationId
    quantity: Quantity


class IngredientExitCreate(IngredientEntryCreate):
    pass


class IngredientEntryRead(BaseModel):
    id: int
    ingredient_id: int
    location_id: LocationId
    quantity: float
    created_at: datetime
    user_uuid: str


class IngredientExitRead(IngredientEntryRead):
    pass


class IngredientOrderRead(BaseModel):
    id: int
    order_type: Literal["inbound", "outbound"]
    ingredient_id: int
    ingredient_name: str
    ingredient_sku: str
    location_id: LocationId
    quantity: float
    created_at: datetime
    user_uuid: str