from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from tinydb import Query, TinyDB

from services.api.database import get_database
from services.api.models import Category, Country, DeleteConfirmation, RateUpdate, StatusUpdate, Supplier, SupplierCreate


router = APIRouter(prefix="/suppliers", tags=["Suppliers"])
Database = Annotated[TinyDB, Depends(get_database)]
SupplierId = Annotated[int, Path(gt=0)]


def find_supplier(database: TinyDB, supplier_id: int):
    record = database.get(doc_id=supplier_id)
    if record is None:
        raise HTTPException(404, "Supplier not found.")
    return {**record, "id": record.doc_id}


@router.post("", response_model=Supplier, status_code=201)
def create_supplier(payload: SupplierCreate, database: Database):
    supplier_id = database.insert({
        **payload.model_dump(mode="json"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return find_supplier(database, supplier_id)


@router.get("", response_model=list[Supplier])
def list_suppliers(database: Database, country: Country | None = None, category: Category | None = None):
    query = Query()
    condition = query.noop()
    if country is not None:
        condition &= query.country == country
    if category is not None:
        condition &= query.categories.any([category])
    return [{**record, "id": record.doc_id} for record in database.search(condition)]


@router.get("/{supplier_id}", response_model=Supplier)
def get_supplier(supplier_id: SupplierId, database: Database):
    return find_supplier(database, supplier_id)


@router.patch("/{supplier_id}/rate", response_model=Supplier)
def update_rate(supplier_id: SupplierId, payload: RateUpdate, database: Database):
    find_supplier(database, supplier_id)
    database.update({
        "rate_per_unit": payload.rate_per_unit,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, doc_ids=[supplier_id])
    return find_supplier(database, supplier_id)


@router.patch("/{supplier_id}/status", response_model=Supplier)
def update_status(supplier_id: SupplierId, payload: StatusUpdate, database: Database):
    find_supplier(database, supplier_id)
    database.update(payload.model_dump(), doc_ids=[supplier_id])
    return find_supplier(database, supplier_id)


@router.delete("/{supplier_id}", response_model=DeleteConfirmation)
def delete_supplier(supplier_id: SupplierId, database: Database):
    find_supplier(database, supplier_id)
    database.remove(doc_ids=[supplier_id])
    return {"detail": "Supplier deleted."}