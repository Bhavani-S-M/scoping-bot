from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
from app.config.database import get_async_session
from app.utils import ratecards
from app import schemas, models
from app.auth import fastapi_users

current_active_user = fastapi_users.current_user(active=True)

router = APIRouter(prefix="/api/companies", tags=["RateCards"])


# COMPANY ROUTES
@router.get("", summary="List all companies (including Sigmoid)")
async def list_companies(
    db: AsyncSession = Depends(get_async_session),
    user: models.User = Depends(current_active_user),
):
    companies = await ratecards.list_companies(db, user_id=user.id)
    return companies


@router.post("", summary="Create a new user-owned company")
async def create_company(
    company: schemas.CompanyCreate,
    db: AsyncSession = Depends(get_async_session),
    user: models.User = Depends(current_active_user),
):
    try:
        new_company = await ratecards.create_company(
            db, company.name, company.currency, user.id
        )
        return new_company
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{company_id}", summary="Delete a user-owned company")
async def delete_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    user: models.User = Depends(current_active_user),
):
    try:
        await ratecards.delete_company(db, company_id, user.id)
        return {"message": "Company and related rate cards deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# RATE CARD ROUTES
@router.get("/{company_id}/ratecards", summary="List rate cards for a specific company")
async def list_ratecards(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    user: models.User = Depends(current_active_user),
):
    cards = await ratecards.list_rate_cards_by_company(db, company_id, user.id)
    return cards


@router.get("/standard/ratecards", summary="List Sigmoid (global) rate cards")
async def list_standard_ratecards(db: AsyncSession = Depends(get_async_session)):
    """Return the global Sigmoid rate card set."""
    sigmoid = await ratecards.get_or_create_sigmoid_company(db)
    return await ratecards.list_rate_cards_by_company(db, sigmoid.id)


@router.post("/{company_id}/ratecards", summary="Add a new rate card")
async def create_ratecard(
    company_id: uuid.UUID,
    data: schemas.RateCardCreate,
    db: AsyncSession = Depends(get_async_session),
    user: models.User = Depends(current_active_user),
):
    try:
        return await ratecards.create_rate_card(
            db, company_id, data.role_name, data.monthly_rate, user.id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/ratecards/{rate_card_id}", summary="Update a rate card")
async def update_ratecard(
    rate_card_id: uuid.UUID,
    data: schemas.RateCardUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: models.User = Depends(current_active_user),
):
    try:
        return await ratecards.update_rate_card(db, rate_card_id, data.monthly_rate)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/ratecards/{rate_card_id}", summary="Delete a rate card")
async def delete_ratecard(
    rate_card_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    user: models.User = Depends(current_active_user),
):
    try:
        await ratecards.delete_rate_card(db, rate_card_id)
        return {"message": f"Rate card {rate_card_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
