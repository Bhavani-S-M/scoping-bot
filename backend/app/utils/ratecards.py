import uuid
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app import models
logger = logging.getLogger(__name__)

SIGMOID_COMPANY_NAME = "Sigmoid"  # Global shared company


# COMPANY HELPERS
async def get_or_create_sigmoid_company(db: AsyncSession) -> models.Company:
    """Ensure the default 'Sigmoid' company exists (shared by all users)."""
    result = await db.execute(
        select(models.Company).filter(models.Company.name == SIGMOID_COMPANY_NAME)
    )
    company = result.scalars().first()
    if not company:
        company = models.Company(
            name=SIGMOID_COMPANY_NAME,
            currency="USD",
            owner_id=None,
        )
        db.add(company)
        await db.commit()
        await db.refresh(company)
        logger.info("Created global Sigmoid company.")
    return company


async def list_companies(db: AsyncSession, user_id: uuid.UUID) -> List[models.Company]:
    """Return all companies owned by the user, plus the global Sigmoid."""
    await get_or_create_sigmoid_company(db)

    q = (
        select(models.Company)
        .filter(
            (models.Company.owner_id == user_id)
            | (models.Company.owner_id.is_(None))
        )
        .order_by(models.Company.name)
    )

    result = await db.execute(q)
    return result.scalars().all()


async def create_company(
    db: AsyncSession,
    name: str,
    currency: str,
    owner_id: uuid.UUID,
) -> models.Company:
    """Create a new user-specific company (no cloning from Sigmoid)."""
    print(f"create_company inputs → name={name}, currency={currency}, owner={owner_id}")

    # Prevent users from creating another "Sigmoid"
    if name.strip().lower() == SIGMOID_COMPANY_NAME.lower():
        raise HTTPException(status_code=400, detail="Reserved name 'Sigmoid' cannot be created.")

    existing = await db.execute(
        select(models.Company)
        .filter(models.Company.name == name.strip())
        .filter(models.Company.owner_id == owner_id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Company with this name already exists.")

    company = models.Company(name=name.strip(), currency=currency, owner_id=owner_id)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    logger.info(f" Created company {company.name} (owner={owner_id})")
    return company


async def delete_company(db: AsyncSession, company_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete a user-owned company safely; prevent deleting Sigmoid."""
    company = await db.get(models.Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Prevent deleting Sigmoid
    if company.name.lower() == SIGMOID_COMPANY_NAME.lower():
        raise HTTPException(status_code=400, detail="Cannot delete the global 'Sigmoid' company.")

    # Enforce ownership
    if company.owner_id != user_id:
        raise HTTPException(status_code=403, detail="You do not own this company.")

    # Delete all associated rate cards
    await db.execute(
        models.RateCard.__table__.delete().where(models.RateCard.company_id == company_id)
    )
    await db.delete(company)
    await db.commit()

    logger.info(f"🗑 Deleted company {company.name} (owner={user_id}) and its rate cards.")
    return True


#  RATE CARD LOGIC
async def list_rate_cards_by_company(
    db: AsyncSession,
    company_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
) -> List[models.RateCard]:
    """
    List rate cards for a specific company.
    If the company is 'Sigmoid', show all rate cards (ignore user_id).
    Otherwise, show only cards owned by the user or shared (user_id=None).
    """
    company = await db.get(models.Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    q = (
        select(models.RateCard)
        .options(
            selectinload(models.RateCard.company),
            selectinload(models.RateCard.user),
        )
        .filter(models.RateCard.company_id == company_id)
    )

    if company.name.lower() != SIGMOID_COMPANY_NAME.lower() and user_id:
        q = q.filter(
            (models.RateCard.user_id == user_id) | (models.RateCard.user_id.is_(None))
        )

    result = await db.execute(q)
    cards = result.scalars().all()
    logger.info(
        f"Found {len(cards)} rate cards for company '{company.name}' (id={company_id})"
    )
    return cards


async def list_rate_cards_auto(
    db: AsyncSession,
    company_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
) -> List[models.RateCard]:
    """Return rate cards for a selected company, or fallback to Sigmoid."""
    sigmoid = await get_or_create_sigmoid_company(db)

    if not company_id:
        company_id = sigmoid.id

    cards = await list_rate_cards_by_company(db, company_id, user_id)
    if not cards and company_id != sigmoid.id:
        logger.info(f"Fallback: using Sigmoid standard rate cards for {company_id}")
        cards = await list_rate_cards_by_company(db, sigmoid.id, user_id)

    return cards


async def get_rate_card(
    db: AsyncSession,
    company_id: uuid.UUID,
    role_name: str,
    user_id: Optional[uuid.UUID] = None,
) -> Optional[models.RateCard]:
    """Get a specific rate card."""
    q = select(models.RateCard).filter(
        models.RateCard.company_id == company_id,
        models.RateCard.role_name.ilike(role_name),
    )
    if user_id:
        q = q.filter(
            (models.RateCard.user_id == user_id) | (models.RateCard.user_id.is_(None))
        )

    result = await db.execute(q)
    rc = result.scalars().first()
    if not rc:
        logger.warning(f" Rate card '{role_name}' not found for company {company_id}")
    return rc


async def create_rate_card(
    db: AsyncSession,
    company_id: uuid.UUID,
    role_name: str,
    monthly_rate: float,
    user_id: Optional[uuid.UUID] = None,
) -> models.RateCard:
    """Create a new rate card for a company."""
    existing = await get_rate_card(db, company_id, role_name, user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rate card already exists for role '{role_name}'",
        )

    rc = models.RateCard(
        company_id=company_id,
        user_id=user_id,
        role_name=role_name.strip(),
        monthly_rate=monthly_rate,
    )
    db.add(rc)
    await db.commit()
    await db.refresh(rc)
    logger.info(f" Created rate card: {role_name} → {monthly_rate}")
    return rc


async def update_rate_card(
    db: AsyncSession,
    rate_card_id: uuid.UUID,
    monthly_rate: float,
) -> models.RateCard:
    """Update a rate card's monthly rate."""
    result = await db.execute(
        select(models.RateCard).filter(models.RateCard.id == rate_card_id)
    )
    rc = result.scalars().first()
    if not rc:
        raise HTTPException(status_code=404, detail="Rate card not found")

    rc.monthly_rate = monthly_rate
    await db.commit()
    await db.refresh(rc)
    logger.info(f" Updated rate card {rc.id} → {monthly_rate}")
    return rc


async def delete_rate_card(db: AsyncSession, rate_card_id: uuid.UUID) -> bool:
    """Delete a rate card."""
    result = await db.execute(
        select(models.RateCard).filter(models.RateCard.id == rate_card_id)
    )
    rc = result.scalars().first()
    if not rc:
        raise HTTPException(status_code=404, detail="Rate card not found")

    await db.delete(rc)
    await db.commit()
    logger.info(f"🗑 Deleted rate card {rate_card_id}")
    return True


# ROLE → RATE MAP
async def get_role_rate_map(
    db: AsyncSession,
    company_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
) -> dict:
    """Return mapping role_name → monthly_rate."""
    cards = await list_rate_cards_by_company(db, company_id, user_id)
    role_map = {}
    for rc in cards:
        if rc.user_id == user_id:
            role_map[rc.role_name.lower()] = rc.monthly_rate
        elif rc.role_name.lower() not in role_map:
            role_map[rc.role_name.lower()] = rc.monthly_rate

    logger.info(f" Built role→rate map ({len(role_map)} roles)")
    return role_map
