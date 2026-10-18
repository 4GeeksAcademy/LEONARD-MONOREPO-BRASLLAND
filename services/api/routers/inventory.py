from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from services.api.app.database import get_db
from services.api.app.models import Ingredient, IngredientEntry, IngredientExit
from services.api.app.schemas import (
    IngredientCreate, IngredientEntryCreate, IngredientEntryRead, IngredientExitCreate,
    IngredientExitRead, IngredientOrderRead, IngredientRead, LocationId,
)
from services.api.auth import CurrentUser


router = APIRouter(prefix="/inventory", tags=["Inventory"])
DatabaseSession = Annotated[Session, Depends(get_db)]
IngredientId = Annotated[int, Path(gt=0)]


def stock_totals(session: Session, location_id: str) -> dict[int, Decimal]:
    entry_query = select(IngredientEntry.ingredient_id, func.sum(IngredientEntry.quantity)).group_by(
        IngredientEntry.ingredient_id
    )
    exit_query = select(IngredientExit.ingredient_id, func.sum(IngredientExit.quantity)).group_by(
        IngredientExit.ingredient_id
    )
    entry_query = entry_query.where(IngredientEntry.location_id == location_id)
    exit_query = exit_query.where(IngredientExit.location_id == location_id)
    entries = dict(session.exec(entry_query).all())
    exits = dict(session.exec(exit_query).all())
    return {
        ingredient_id: entries.get(ingredient_id, Decimal(0)) - exits.get(ingredient_id, Decimal(0))
        for ingredient_id in entries.keys() | exits.keys()
    }


def ingredient_response(ingredient: Ingredient, current_stock: Decimal) -> IngredientRead:
    return IngredientRead(
        id=ingredient.id,
        name=ingredient.name,
        sku=ingredient.sku,
        category=ingredient.category,
        unit=ingredient.unit,
        current_stock=float(current_stock),
    )


def ingredient_or_404(session: Session, ingredient_id: int, *, lock: bool = False) -> Ingredient:
    query = select(Ingredient).where(Ingredient.id == ingredient_id)
    if lock:
        query = query.with_for_update()
    ingredient = session.exec(query).first()
    if ingredient is None:
        raise HTTPException(404, "Ingredient not found.")
    return ingredient


def order_response(order, order_type: str) -> IngredientOrderRead:
    return IngredientOrderRead(
        id=order.id,
        order_type=order_type,
        ingredient_id=order.ingredient_id,
        ingredient_name=order.ingredient.name,
        ingredient_sku=order.ingredient.sku,
        location_id=order.location_id,
        quantity=float(order.quantity),
        created_at=order.created_at,
        user_uuid=order.user_uuid,
    )


@router.get("/products", response_model=list[IngredientRead])
def list_ingredients(session: DatabaseSession, location_id: LocationId):
    totals = stock_totals(session, location_id)
    ingredients = session.exec(select(Ingredient).order_by(Ingredient.name, Ingredient.id)).all()
    return [ingredient_response(item, totals.get(item.id, Decimal(0))) for item in ingredients]


@router.post("/products", response_model=IngredientRead, status_code=201)
def create_ingredient(payload: IngredientCreate, session: DatabaseSession, current_user: CurrentUser):
    ingredient = Ingredient(**payload.model_dump())
    session.add(ingredient)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(409, "An ingredient with this SKU already exists.") from error
    session.refresh(ingredient)
    return ingredient_response(ingredient, Decimal(0))


@router.get("/products/{ingredient_id}", response_model=IngredientRead)
def get_ingredient(
    ingredient_id: IngredientId, session: DatabaseSession, location_id: LocationId,
):
    ingredient = ingredient_or_404(session, ingredient_id)
    return ingredient_response(ingredient, stock_totals(session, location_id).get(ingredient_id, Decimal(0)))


@router.post("/orders/inbound", response_model=IngredientEntryRead, status_code=201)
def create_inbound_order(
    payload: IngredientEntryCreate, session: DatabaseSession, current_user: CurrentUser,
):
    ingredient_or_404(session, payload.ingredient_id)
    order = IngredientEntry(
        **payload.model_dump(),
        created_at=datetime.now(timezone.utc),
        user_uuid=current_user.id,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return IngredientEntryRead(
        id=order.id,
        ingredient_id=order.ingredient_id,
        location_id=order.location_id,
        quantity=float(order.quantity),
        created_at=order.created_at,
        user_uuid=order.user_uuid,
    )


@router.post("/orders/outbound", response_model=IngredientExitRead, status_code=201)
def create_outbound_order(
    payload: IngredientExitCreate, session: DatabaseSession, current_user: CurrentUser,
):
    ingredient_or_404(session, payload.ingredient_id, lock=True)
    available = stock_totals(session, payload.location_id).get(payload.ingredient_id, Decimal(0))
    if payload.quantity > available:
        raise HTTPException(
            400,
            f"Insufficient stock at {payload.location_id}: {available} available, {payload.quantity} requested.",
        )
    order = IngredientExit(
        **payload.model_dump(),
        created_at=datetime.now(timezone.utc),
        user_uuid=current_user.id,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return IngredientExitRead(
        id=order.id,
        ingredient_id=order.ingredient_id,
        location_id=order.location_id,
        quantity=float(order.quantity),
        created_at=order.created_at,
        user_uuid=order.user_uuid,
    )


@router.get("/orders", response_model=list[IngredientOrderRead])
def list_orders(session: DatabaseSession, location_id: LocationId | None = None):
    inbound_query = select(IngredientEntry).options(selectinload(IngredientEntry.ingredient))
    outbound_query = select(IngredientExit).options(selectinload(IngredientExit.ingredient))
    if location_id is not None:
        inbound_query = inbound_query.where(IngredientEntry.location_id == location_id)
        outbound_query = outbound_query.where(IngredientExit.location_id == location_id)
    inbound: Sequence[IngredientEntry] = session.exec(inbound_query).all()
    outbound: Sequence[IngredientExit] = session.exec(outbound_query).all()
    orders = [order_response(order, "inbound") for order in inbound]
    orders.extend(order_response(order, "outbound") for order in outbound)
    return sorted(orders, key=lambda order: (order.created_at, order.id), reverse=True)