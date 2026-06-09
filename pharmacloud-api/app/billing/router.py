from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import uuid
from pydantic import BaseModel

from app.shared.database import get_db
from app.dependencies import get_current_user
from app.models import Tenant, Plan, Subscription, Staff

router = APIRouter(prefix="/billing", tags=["Billing & Subscriptions"])

# Pydantic Schemas
class PlanResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    price_monthly: float
    price_yearly: float
    max_users: int
    max_medicines: int
    max_branches: int
    features: Dict[str, Any]
    is_active: bool

    class Config:
        from_attributes = True

class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    billing_cycle: str
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    external_id: Optional[str] = None
    plan_name: Optional[str] = None

    class Config:
        from_attributes = True

class CheckoutRequest(BaseModel):
    plan_id: uuid.UUID
    payment_method_id: Optional[str] = None


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)):
    """Retrieve all active platform plans."""
    stmt = select(Plan).filter(Plan.is_active == True)
    result = await db.execute(stmt)
    plans = result.scalars().all()
    
    # Map Decimal to float for Pydantic validation compatibility
    formatted_plans = []
    for p in plans:
        formatted_plans.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "price_monthly": float(p.price_monthly),
            "price_yearly": float(p.price_yearly),
            "max_users": p.max_users,
            "max_medicines": p.max_medicines,
            "max_branches": p.max_branches,
            "features": p.features or {},
            "is_active": p.is_active
        })
    return formatted_plans


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Retrieve the current subscription for the tenant."""
    # Run query inside the tenant's transaction / RLS context
    stmt = (
        select(Subscription, Plan.name)
        .join(Plan, Subscription.plan_id == Plan.id)
        .filter(Subscription.tenant_id == current_user.tenant_id)
        .order_by(Subscription.created_at.desc())
    )
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found for this tenant."
        )
        
    sub, plan_name = row
    return {
        "id": sub.id,
        "tenant_id": sub.tenant_id,
        "plan_id": sub.plan_id,
        "status": sub.status,
        "billing_cycle": sub.billing_cycle,
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
        "cancelled_at": sub.cancelled_at,
        "trial_ends_at": sub.trial_ends_at,
        "external_id": sub.external_id,
        "plan_name": plan_name
    }


@router.post("/checkout", response_model=SubscriptionResponse)
async def checkout_plan(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Subscribe or upgrade/downgrade to a different plan."""
    # 1. Fetch Plan (requires bypassing RLS temporarily as plans are platform level,
    # but select on plans table is generally permitted or doesn't have RLS restrictions)
    plan_stmt = select(Plan).filter(Plan.id == payload.plan_id, Plan.is_active == True)
    plan_result = await db.execute(plan_stmt)
    plan = plan_result.scalars().first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found or inactive."
        )

    # 2. Upgrade Tenant plan reference
    tenant_stmt = select(Tenant).filter(Tenant.id == current_user.tenant_id)
    tenant_result = await db.execute(tenant_stmt)
    tenant = tenant_result.scalars().first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found."
        )
    tenant.plan_id = plan.id
    db.add(tenant)

    # 3. Create or Update active Subscription
    sub_stmt = (
        select(Subscription)
        .filter(Subscription.tenant_id == current_user.tenant_id)
        .order_by(Subscription.created_at.desc())
    )
    sub_result = await db.execute(sub_stmt)
    subscription = sub_result.scalars().first()
    
    now = datetime.now(timezone.utc)
    if subscription:
        subscription.plan_id = plan.id
        subscription.status = "active"
        subscription.billing_cycle = "monthly"
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=30)
        subscription.cancelled_at = None
        subscription.updated_at = now
    else:
        subscription = Subscription(
            id=uuid.uuid4(),
            tenant_id=current_user.tenant_id,
            plan_id=plan.id,
            status="active",
            billing_cycle="monthly",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now
        )
        db.add(subscription)

    await db.commit()
    await db.refresh(subscription)

    return {
        "id": subscription.id,
        "tenant_id": subscription.tenant_id,
        "plan_id": subscription.plan_id,
        "status": subscription.status,
        "billing_cycle": subscription.billing_cycle,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "cancelled_at": subscription.cancelled_at,
        "trial_ends_at": subscription.trial_ends_at,
        "external_id": subscription.external_id,
        "plan_name": plan.name
    }


@router.post("/subscription/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Cancel the active subscription."""
    stmt = (
        select(Subscription)
        .filter(Subscription.tenant_id == current_user.tenant_id)
        .order_by(Subscription.created_at.desc())
    )
    result = await db.execute(stmt)
    subscription = result.scalars().first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found."
        )

    now = datetime.now(timezone.utc)
    subscription.status = "cancelled"
    subscription.cancelled_at = now
    subscription.updated_at = now
    
    # We also need to get the Plan name to return
    plan_stmt = select(Plan.name).filter(Plan.id == subscription.plan_id)
    plan_result = await db.execute(plan_stmt)
    plan_name = plan_result.scalar() or "Pro"

    await db.commit()
    await db.refresh(subscription)

    return {
        "id": subscription.id,
        "tenant_id": subscription.tenant_id,
        "plan_id": subscription.plan_id,
        "status": subscription.status,
        "billing_cycle": subscription.billing_cycle,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "cancelled_at": subscription.cancelled_at,
        "trial_ends_at": subscription.trial_ends_at,
        "external_id": subscription.external_id,
        "plan_name": plan_name
    }
