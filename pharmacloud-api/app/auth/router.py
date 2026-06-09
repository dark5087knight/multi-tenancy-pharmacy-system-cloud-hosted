from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Header
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import text, func
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid
import re

from app.shared.database import get_db
from app.shared.exceptions import AuthException, ValidationException
from app.shared.responses import success_response
from app.auth.service import (
    hash_password, verify_password, create_access_token, create_refresh_token, decode_token
)
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, TokenUserResponse
from app.dependencies import get_current_user
from app.models import Tenant, Branch, Plan, Staff, Role, Permission, UserRole, Subscription

router = APIRouter(prefix="/auth", tags=["Authentication"])

def slugify(name: str) -> str:
    """Generate a clean URL slug from tenant name."""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s_-]+', '-', name)
    return name

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Since we are logging in, we query globally (no RLS is set yet)
    # The default connection role 'dark' has BYPASSRLS permissions.
    stmt = select(Staff).filter(Staff.email == payload.email, Staff.deleted_at == None).options(
        selectinload(Staff.roles).selectinload(Role.permissions),
        selectinload(Staff.tenant)
    )
    result = await db.execute(stmt)
    staff = result.scalars().first()
    
    if not staff:
        # Check if a Tenant exists with this email address, but has no admin users
        tenant_stmt = select(Tenant).filter(Tenant.email == payload.email)
        tenant_res = await db.execute(tenant_stmt)
        tenant = tenant_res.scalars().first()
        if tenant:
            # Check if this tenant has any staff with admin/owner roles
            admin_stmt = select(Staff).join(Staff.roles).filter(
                Staff.tenant_id == tenant.id,
                Role.name.in_(["admin", "owner"])
            )
            admin_res = await db.execute(admin_stmt)
            if not admin_res.scalars().first():
                # Force admin creation!
                raise HTTPException(
                    status_code=428,
                    detail={
                        "code": "NO_ADMIN_USER",
                        "tenant_id": str(tenant.id),
                        "message": "No admin user exists for this tenant. Setup is required."
                    }
                )
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    if staff.status != "active":
        raise HTTPException(status_code=403, detail="Staff account is inactive.")

    # Verify password (handles SHA-256 fallback)
    if not verify_password(payload.password, staff.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Check tenant subscription status
    sub_stmt = select(Subscription).filter(Subscription.tenant_id == staff.tenant_id).order_by(Subscription.created_at.desc())
    sub_res = await db.execute(sub_stmt)
    subscription = sub_res.scalars().first()
    
    role_name = staff.roles[0].name if staff.roles else "cashier"
    if not subscription or subscription.status not in ["active", "trialing"]:
        # Inactive subscription: only admin/owner can log in (to access billing and renew)
        if role_name not in ["admin", "owner"]:
            raise HTTPException(
                status_code=402,
                detail="Subscription is inactive or expired. Please contact the administrator."
            )

    # Upgrade to bcrypt if password hash is SHA-256
    if len(staff.password_hash) == 64:
        staff.password_hash = hash_password(payload.password)
        db.add(staff)

    # Update last seen timestamp
    staff.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(staff)

    # Generate JWT tokens
    role_name = staff.roles[0].name if staff.roles else "cashier"
    permissions = []
    if staff.roles:
        permissions = [p.code for p in staff.roles[0].permissions]

    token_data = {
        "sub": str(staff.id),
        "tid": str(staff.tenant_id),
        "role": role_name,
        "perms": permissions
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Set HttpOnly cookie for web/React client compatibility
    response.set_cookie(
        key="session_id",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production
        max_age=30 * 24 * 3600,  # 30 days
    )

    # Return standard response matching expected client parameters
    user_info = {
        "id": str(staff.id),
        "name": staff.name,
        "email": staff.email,
        "role": role_name,
        "status": staff.status,
        "shift": staff.shift,
        "joinedAt": staff.joined_at.isoformat(),
        "lastSeen": staff.last_seen_at.isoformat() if staff.last_seen_at else "",
        "pharmacyName": staff.tenant.name if staff.tenant else "Caduceus Pharmacy"
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "session_token": access_token,  # Backward compatibility for Flutter client
        "user": user_info
    }


@router.post("/register")
async def register(payload: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # 1. Check if email already registered (both staff and tenant)
    email_stmt = select(Staff).filter(Staff.email == payload.email)
    email_result = await db.execute(email_stmt)
    if email_result.scalars().first():
        raise HTTPException(status_code=400, detail="Email is already registered.")

    tenant_email_stmt = select(Tenant).filter(Tenant.email == payload.email)
    tenant_email_result = await db.execute(tenant_email_stmt)
    if tenant_email_result.scalars().first():
        raise HTTPException(status_code=400, detail="A pharmacy with this email is already registered.")

    # 2. Get or create platform Plan
    plan_stmt = select(Plan).filter(Plan.slug == "pro")
    plan_result = await db.execute(plan_stmt)
    plan = plan_result.scalars().first()

    if not plan:
        plan = Plan(
            id=uuid.uuid4(),
            name="Pro",
            slug="pro",
            description="Professional plan seeded on registration.",
            price_monthly=99.00,
            price_yearly=990.00,
            max_users=50,
            max_medicines=50000,
            max_branches=10,
            features={"all": True},
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(plan)

    # 3. Create Tenant
    tenant_slug = slugify(payload.pharmacy_name)
    # Check if slug exists, append random if needed
    slug_stmt = select(Tenant).filter(Tenant.slug == tenant_slug)
    slug_result = await db.execute(slug_stmt)
    if slug_result.scalars().first():
        tenant_slug = f"{tenant_slug}-{str(uuid.uuid4())[:8]}"

    tenant = Tenant(
        id=uuid.uuid4(),
        name=payload.pharmacy_name,
        slug=tenant_slug,
        email=payload.email,
        status="active",
        plan_id=plan.id,
        country="IQ",
        timezone="Asia/Baghdad",
        locale="en",
        currency="IQD",
        settings={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(tenant)
    await db.flush()

    # 4. Create default Subscription
    subscription = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        plan_id=plan.id,
        status="active",
        billing_cycle="monthly",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(subscription)

    # 5. Create main Branch
    branch = Branch(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Main Branch",
        address="Pharmacy Address",
        is_main=True,
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(branch)

    # 6. Ensure permissions catalog exists globally
    permissions_list = [
        ("manage_users", "staff", "Manage staff accounts"),
        ("manage_roles", "staff", "Manage user roles and permissions"),
        ("view_inventory", "medicines", "View inventory and medicines"),
        ("manage_inventory", "medicines", "Add, edit, or delete medicines"),
        ("view_sales", "sales", "View sales invoices and transactions"),
        ("manage_sales", "sales", "Create, edit, or refund sales transactions"),
        ("view_reports", "reports", "View sales, financial, and inventory reports"),
        ("manage_finance", "finance", "Manage payments and pricing"),
        ("view_prescriptions", "prescriptions", "View prescriptions"),
        ("manage_prescriptions", "prescriptions", "Verify and fulfill prescriptions"),
    ]
    
    permissions_map = {}
    for code, mod, desc in permissions_list:
        perm_stmt = select(Permission).filter(Permission.code == code)
        perm_result = await db.execute(perm_stmt)
        perm = perm_result.scalars().first()
        if not perm:
            perm = Permission(
                id=uuid.uuid4(),
                code=code,
                module=mod,
                description=desc,
                created_at=datetime.now(timezone.utc)
            )
            db.add(perm)
        permissions_map[code] = perm

    # 7. Create Seed Roles for this Tenant
    role_admin = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="admin",
        description="Administrator - Full access",
        is_system=True,
        permissions=list(permissions_map.values()),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(role_admin)

    role_pharmacist = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="pharmacist",
        description="Pharmacist - Can manage inventory and prescriptions",
        is_system=True,
        permissions=[permissions_map[c] for c in ["view_inventory", "manage_inventory", "view_sales", "manage_sales", "view_prescriptions", "manage_prescriptions"] if c in permissions_map],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(role_pharmacist)

    role_cashier = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="cashier",
        description="Cashier - Can perform sales transactions",
        is_system=True,
        permissions=[permissions_map[c] for c in ["view_inventory", "view_sales", "manage_sales", "view_prescriptions"] if c in permissions_map],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(role_cashier)

    role_manager = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="manager",
        description="Store Manager - Can view reports and manage store operations",
        is_system=True,
        permissions=[permissions_map[c] for c in ["view_inventory", "manage_inventory", "view_sales", "manage_sales", "view_reports", "view_prescriptions", "manage_prescriptions"] if c in permissions_map],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(role_manager)

    # 8. Create Owner Staff member
    owner = Staff(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Owner",
        email=payload.email,
        password_hash=hash_password(payload.password),
        status="active",
        shift="morning",
        joined_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    owner.roles.append(role_admin)
    db.add(owner)
    
    # Commit all additions atomically
    try:
        await db.commit()
        await db.refresh(owner)
    except Exception as e:
        await db.rollback()
        raise e

    # 9. Return login response immediately
    token_data = {
        "sub": str(owner.id),
        "tid": str(owner.tenant_id),
        "role": "admin",
        "perms": [p.code for p in permissions_map.values()]
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    response.set_cookie(
        key="session_id",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=30 * 24 * 3600,  # 30 days
    )

    user_info = {
        "id": str(owner.id),
        "name": owner.name,
        "email": owner.email,
        "role": "admin",
        "status": owner.status,
        "shift": owner.shift,
        "joined_at": owner.joined_at.isoformat(),
        "last_seen": "",
        "pharmacy_name": payload.pharmacy_name
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "session_token": access_token,
        "user": user_info
    }


@router.post("/refresh")
async def refresh_token(response: Response, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
    
    token = authorization[7:]
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token.")

    # Re-issue access token
    access_token_data = {
        "sub": payload.get("sub"),
        "tid": payload.get("tid"),
        "role": payload.get("role"),
        "perms": payload.get("perms")
    }

    new_access_token = create_access_token(access_token_data)

    response.set_cookie(
        key="session_id",
        value=new_access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=30 * 24 * 3600,  # 30 days
    )

    return {
        "access_token": new_access_token,
        "session_token": new_access_token
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="session_id")
    return success_response({"detail": "Logged out successfully."})


@router.get("/me")
async def get_me(current_user: Staff = Depends(get_current_user)):
    role_name = current_user.roles[0].name if current_user.roles else "cashier"
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": role_name,
        "status": current_user.status,
        "shift": current_user.shift,
        "joinedAt": current_user.joined_at.isoformat(),
        "lastSeen": current_user.last_seen_at.isoformat() if current_user.last_seen_at else "",
        "pharmacyName": current_user.tenant.name if current_user.tenant else "Caduceus Pharmacy"
    }


class SetupAdminRequest(BaseModel):
    tenant_id: uuid.UUID
    name: str
    email: str
    password: str

@router.post("/setup-admin")
async def setup_first_admin(payload: SetupAdminRequest, db: AsyncSession = Depends(get_db)):
    # Check if tenant exists
    tenant_stmt = select(Tenant).filter(Tenant.id == payload.tenant_id)
    tenant_res = await db.execute(tenant_stmt)
    tenant = tenant_res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")
        
    # Check if any admin/owner exists for this tenant
    admin_stmt = select(Staff).join(Staff.roles).filter(
        Staff.tenant_id == payload.tenant_id,
        Role.name.in_(["admin", "owner"])
    )
    admin_res = await db.execute(admin_stmt)
    if admin_res.scalars().first():
        raise HTTPException(status_code=400, detail="Admin already exists for this tenant.")
        
    # Resolve or create Admin Role for this Tenant
    role_stmt = select(Role).filter(Role.tenant_id == payload.tenant_id, Role.name == "admin")
    role_res = await db.execute(role_stmt)
    role_admin = role_res.scalars().first()
    if not role_admin:
        # Get all global permissions to assign to admin
        from app.models import Permission
        perm_stmt = select(Permission)
        perm_res = await db.execute(perm_stmt)
        permissions = perm_res.scalars().all()
        
        role_admin = Role(
            id=uuid.uuid4(),
            tenant_id=payload.tenant_id,
            name="admin",
            description="Administrator - Full access",
            is_system=True,
            permissions=permissions,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(role_admin)

        # Seed default roles as well
        permissions_dict = {p.code: p for p in permissions}
        
        role_pharmacist = Role(
            id=uuid.uuid4(),
            tenant_id=payload.tenant_id,
            name="pharmacist",
            description="Pharmacist - Can manage inventory and prescriptions",
            is_system=True,
            permissions=[permissions_dict[c] for c in ["view_inventory", "manage_inventory", "view_sales", "manage_sales", "view_prescriptions", "manage_prescriptions"] if c in permissions_dict],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(role_pharmacist)

        role_cashier = Role(
            id=uuid.uuid4(),
            tenant_id=payload.tenant_id,
            name="cashier",
            description="Cashier - Can perform sales transactions",
            is_system=True,
            permissions=[permissions_dict[c] for c in ["view_inventory", "view_sales", "manage_sales", "view_prescriptions"] if c in permissions_dict],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(role_cashier)

        role_manager = Role(
            id=uuid.uuid4(),
            tenant_id=payload.tenant_id,
            name="manager",
            description="Store Manager - Can view reports and manage store operations",
            is_system=True,
            permissions=[permissions_dict[c] for c in ["view_inventory", "manage_inventory", "view_sales", "manage_sales", "view_reports", "view_prescriptions", "manage_prescriptions"] if c in permissions_dict],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(role_manager)
        
    admin = Staff(
        id=uuid.uuid4(),
        tenant_id=payload.tenant_id,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        status="active",
        shift="morning",
        joined_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    admin.roles.append(role_admin)
    db.add(admin)
    await db.commit()
    return {"detail": "Admin user created successfully."}


@router.get("/tenant-status")
async def get_tenant_status(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    # Count other staff (excluding current user)
    staff_count_stmt = select(func.count()).select_from(Staff).filter(
        Staff.tenant_id == current_user.tenant_id,
        Staff.id != current_user.id
    )
    staff_res = await db.execute(staff_count_stmt)
    staff_count = staff_res.scalar() or 0
    
    # Count inventory medicines
    from app.models import Medicine
    med_count_stmt = select(func.count()).select_from(Medicine).filter(
        Medicine.tenant_id == current_user.tenant_id
    )
    med_res = await db.execute(med_count_stmt)
    med_count = med_res.scalar() or 0
    
    # Count suppliers
    from app.models import Supplier
    sup_count_stmt = select(func.count()).select_from(Supplier).filter(
        Supplier.tenant_id == current_user.tenant_id
    )
    sup_res = await db.execute(sup_count_stmt)
    sup_count = sup_res.scalar() or 0
    
    is_empty = (staff_count == 0 and med_count == 0 and sup_count == 0)
    
    return {
        "is_empty": is_empty,
        "staff_count": staff_count,
        "med_count": med_count,
        "sup_count": sup_count
    }
