from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from shared.incidents import (
    IncidentBranch, IncidentCategory, IncidentOrigin, IncidentStatus,
    validate_incident_values,
)


VALID_CATEGORIES = (
    "carne", "verduras_y_hortalizas", "salsas_y_condimentos", "bebidas",
    "packaging", "productos_limpieza", "lacteos", "carbon_y_combustible",
)
Category = Literal[
    "carne", "verduras_y_hortalizas", "salsas_y_condimentos", "bebidas",
    "packaging", "productos_limpieza", "lacteos", "carbon_y_combustible",
]
Status = Literal["active", "suspended"]
Country = Literal["Colombia", "USA"]
Rate = Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    country: Country
    categories: list[Category] = Field(min_length=1)
    rate_per_unit: Rate
    currency: Literal["COP", "USD"]
    status: Status
    contact_email: EmailStr | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def currency_matches_country(self):
        expected = "COP" if self.country == "Colombia" else "USD"
        if self.currency != expected:
            raise ValueError(f"Suppliers in {self.country} must use {expected}.")
        return self


class Supplier(BaseModel):
    id: int
    name: str
    country: Country
    categories: list[Category]
    rate_per_unit: float
    currency: Literal["COP", "USD"]
    status: Status
    contact_email: EmailStr | None = None
    notes: str | None = None
    updated_at: datetime


class DeleteConfirmation(BaseModel):
    detail: str


class RateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rate_per_unit: Rate


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Status


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=5)
    category: IncidentCategory
    status: IncidentStatus
    origin: IncidentOrigin
    branch: IncidentBranch

    @model_validator(mode="after")
    def validate_shared_fields(self):
        errors = validate_incident_values(self.model_dump(mode="json"))
        if errors:
            raise ValueError("; ".join(f"{field}: {message}" for field, message in errors.items()))
        return self


class Incident(BaseModel):
    id: int
    title: str
    description: str
    category: IncidentCategory
    status: IncidentStatus
    origin: IncidentOrigin
    branch: IncidentBranch
    created_at: datetime
    updated_at: datetime


class IncidentSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    by_origin: dict[str, int]
    by_branch: dict[str, int]


class IncidentStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: IncidentStatus