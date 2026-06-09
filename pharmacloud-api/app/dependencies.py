from fastapi import Depends, Cookie, Header, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import text
from typing import Optional
import uuid

from app.shared.database import get_db
from app.shared.exceptions import AuthException, PermissionException
from app.auth.service import decode_token
from app.models import Staff, Role, Subscription

async def get_current_user(
    request: Request,
    session_id: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Staff:
    """
    Extract JWT token from headers or cookies, decode it, and load the Staff member
    under the PostgreSQL RLS tenant context.
    """
    token = None
    
    # 1. Try to get token from Authorization header
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    
    # 2. Try to get token from session_id cookie
    elif session_id:
        # Check if cookie contains "session_id=" prefix
        if session_id.startswith("session_id="):
            token = session_id.replace("session_id=", "")
        else:
            token = session_id
            
    # 3. Try to get token from custom header
    elif x_session_id:
        token = x_session_id

    if not token:
        raise AuthException("Unauthorized. No session token provided.")

    # Decode JWT token
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise AuthException(f"Unauthorized. {str(e)}")

    if payload.get("type") != "access":
        raise AuthException("Unauthorized. Invalid token type.")

    staff_id_str = payload.get("sub")
    tenant_id_str = payload.get("tid")
    
    if not staff_id_str or not tenant_id_str:
        raise AuthException("Unauthorized. Invalid token payload structure.")

    try:
        staff_uuid = uuid.UUID(staff_id_str)
        tenant_uuid = uuid.UUID(tenant_id_str)
    except ValueError:
        raise AuthException("Unauthorized. Invalid UUID format in token claims.")

    # Configure PostgreSQL RLS variables BEFORE running any database query in this transaction!
    await db.execute(text("SET ROLE pharmacy_app"))
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, TRUE)"),
        {"tenant_id": str(tenant_uuid)}
    )
    await db.execute(
        text("SELECT set_config('app.current_staff_id', :staff_id, TRUE)"),
        {"staff_id": str(staff_uuid)}
    )

    # Fetch the staff member along with roles, permissions, and tenant in this RLS context
    stmt = select(Staff).filter(Staff.id == staff_uuid, Staff.deleted_at == None).options(
        selectinload(Staff.roles).selectinload(Role.permissions),
        selectinload(Staff.tenant)
    )
    result = await db.execute(stmt)
    staff = result.scalars().first()
    
    if not staff:
        raise AuthException("Unauthorized. Staff member not found under current tenant context.")
        
    if staff.status != "active":
        raise AuthException("Unauthorized. Staff account is inactive.")

    # Check tenant subscription status
    sub_stmt = select(Subscription).filter(Subscription.tenant_id == staff.tenant_id).order_by(Subscription.created_at.desc())
    sub_res = await db.execute(sub_stmt)
    subscription = sub_res.scalars().first()
    
    if not subscription or subscription.status not in ["active", "trialing"]:
        path = request.url.path
        # Allow access to billing endpoints, logout, and health probe so they can manage payments or log out
        if not (path.startswith("/billing") or path == "/auth/logout" or path == "/health" or path.startswith("/health/")):
            raise HTTPException(
                status_code=402,
                detail="Subscription is inactive or expired. Access restricted."
            )

    return staff

def require_permission(permission: str):
    """Factory dependency to enforce specific RBAC permissions."""
    async def dependency(current_user: Staff = Depends(get_current_user)) -> Staff:
        user_permissions = []
        for role in current_user.roles:
            user_permissions.extend([p.code for p in role.permissions])
            
        if permission not in user_permissions:
            raise PermissionException(f"Forbidden. Missing permission: {permission}")
            
        return current_user
    return dependency
