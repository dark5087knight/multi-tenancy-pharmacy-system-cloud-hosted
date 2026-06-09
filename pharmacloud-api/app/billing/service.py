from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
import uuid

from app.shared.exceptions import PlanLimitException
from app.models import Tenant, Plan, Staff, Medicine, Branch

async def check_plan_limit(db: AsyncSession, tenant_id: uuid.UUID, resource: str):
    """
    Check if the tenant has reached the limits allowed by their subscribed plan.
    Raises PlanLimitException if limits are exceeded.
    """
    # Fetch tenant along with plan
    tenant_stmt = select(Tenant).filter(Tenant.id == tenant_id).options(selectinload(Tenant.plan))
    tenant_res = await db.execute(tenant_stmt)
    tenant = tenant_res.scalars().first()
    
    if not tenant or not tenant.plan:
        return

    plan = tenant.plan

    if resource == "staff":
        count_stmt = select(func.count()).select_from(Staff).filter(Staff.tenant_id == tenant_id, Staff.deleted_at == None)
        count_res = await db.execute(count_stmt)
        current_count = count_res.scalar() or 0
        if current_count >= plan.max_users:
            raise PlanLimitException(f"Your '{plan.name}' plan allows a maximum of {plan.max_users} staff members.")

    elif resource == "medicines":
        count_stmt = select(func.count()).select_from(Medicine).filter(Medicine.tenant_id == tenant_id, Medicine.deleted_at == None)
        count_res = await db.execute(count_stmt)
        current_count = count_res.scalar() or 0
        if current_count >= plan.max_medicines:
            raise PlanLimitException(f"Your '{plan.name}' plan allows a maximum of {plan.max_medicines} medicines.")

    elif resource == "branches":
        count_stmt = select(func.count()).select_from(Branch).filter(Branch.tenant_id == tenant_id)
        count_res = await db.execute(count_stmt)
        current_count = count_res.scalar() or 0
        if current_count >= plan.max_branches:
            raise PlanLimitException(f"Your '{plan.name}' plan allows a maximum of {plan.max_branches} branches.")
