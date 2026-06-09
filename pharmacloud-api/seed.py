import asyncio
import uuid
import re
import os
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.future import select

# Ensure the app root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.shared.database import AsyncSessionLocal, engine as db_engine
from app.models import Plan, Tenant, Subscription, Branch, Permission, Role, Staff
from app.auth.service import hash_password

def get_postgres_urls():
    """
    Parse database settings to construct connection strings:
    1. A sync connection string for postgres (system DB) to check/create the target DB.
    2. A sync connection string for the target DB (for checks if needed).
    3. The database name.
    """
    async_url = settings.DATABASE_URL
    
    # Replace +asyncpg with standard postgresql for sync engine
    sync_url = async_url.replace("+asyncpg", "")
    
    # Match pattern: protocol://user:pass@host:port/dbname
    match = re.match(r"(postgresql://[^/]+)/([^?#]+)", sync_url)
    if match:
        base_url = match.group(1)
        db_name = match.group(2)
        postgres_url = f"{base_url}/postgres"
        return postgres_url, sync_url, db_name
    else:
        raise ValueError(f"Could not parse DATABASE_URL: {async_url}")

def init_db_if_not_exists():
    """
    Check if the target database exists. If not, create it.
    """
    postgres_url, _, db_name = get_postgres_urls()
    print(f"Connecting to system DB: postgres at {postgres_url}...")
    
    engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        try:
            # Query pg_database to check if database exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"))
            exists = result.scalar() is not None
            if not exists:
                print(f"Database '{db_name}' does not exist. Creating...")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"Database '{db_name}' created successfully.")
            else:
                print(f"Database '{db_name}' already exists.")
        except Exception as e:
            print(f"Error checking/creating database '{db_name}': {e}")
            raise e

def run_migrations():
    """
    Run Alembic migrations programmatically or via subprocess.
    """
    print("Running database migrations via Alembic...")
    api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Run 'alembic upgrade head' in the API root directory
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=api_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    if result.returncode != 0:
        print("Alembic migrations failed! Error output:")
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("Alembic migrations failed.")
    
    print("Migrations applied successfully!")
    print(result.stdout)

def get_datetime_now(d: float) -> datetime:
    """Helper to get timezone-aware datetime offset by d days."""
    now = datetime.now(timezone.utc)
    return now + timedelta(days=d)

async def seed_core_data(db):
    """
    Seed minimal base data needed for a clean installation:
    - Default plans (Starter, Pro, Enterprise)
    - Default permissions
    - Default tenant (Default Pharmacy)
    - Default subscription
    - Default branch
    - Default roles (admin, pharmacist, cashier, manager)
    - Default admin staff user (admin@pharmacy.com / admin)
    """
    # 1. Check if database is already seeded
    plan_check = await db.execute(select(Plan))
    if plan_check.scalars().first() is not None:
        print("Database already contains seed data (plans found). Skipping seeding.")
        return

    print("Seeding core database entities...")

    # 2. Platform Plans
    plan_starter = Plan(
        id=uuid.uuid4(),
        name="Starter",
        slug="starter",
        description="For independent pharmacies getting started.",
        price_monthly=29.00,
        price_yearly=290.00,
        max_users=2,
        max_medicines=2000,
        max_branches=1,
        features={"pos": True, "inventory": True, "reports": False},
        is_active=True,
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )
    db.add(plan_starter)

    plan_pro = Plan(
        id=uuid.uuid4(),
        name="Pro",
        slug="pro",
        description="Professional multi-tenant plan with full features.",
        price_monthly=79.00,
        price_yearly=790.00,
        max_users=50,
        max_medicines=50000,
        max_branches=10,
        features={"all": True},
        is_active=True,
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )
    db.add(plan_pro)

    plan_enterprise = Plan(
        id=uuid.uuid4(),
        name="Enterprise",
        slug="enterprise",
        description="For multi-branch networks and chains.",
        price_monthly=199.00,
        price_yearly=1990.00,
        max_users=999,
        max_medicines=999999,
        max_branches=999,
        features={"all": True, "sso": True, "sla": True},
        is_active=True,
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )
    db.add(plan_enterprise)

    # Commit plans so we can reference them
    await db.commit()
    await db.refresh(plan_pro)

    # 3. Default Tenant
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Default Pharmacy",
        slug="default",
        email="contact@defaultpharm.com",
        phone="+1 555-0100",
        address="100 Pharmacy Blvd",
        country="IQ",
        timezone="Asia/Baghdad",
        locale="en",
        currency="IQD",
        logo_url=None,
        status="active",
        settings={},
        plan_id=plan_pro.id,
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    # 4. Default Subscription
    subscription = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        plan_id=plan_pro.id,
        status="active",
        billing_cycle="monthly",
        current_period_start=get_datetime_now(-5),
        current_period_end=get_datetime_now(25),
        created_at=get_datetime_now(-5),
        updated_at=get_datetime_now(-5)
    )
    db.add(subscription)

    # 5. Default Branch
    branch = Branch(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Main Branch",
        address="100 Pharmacy Blvd",
        phone="+1 555-0100",
        is_main=True,
        status="active",
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)

    # 6. Platform Permissions List
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
    
    perms = {}
    for code, mod, desc in permissions_list:
        p = Permission(
            id=uuid.uuid4(),
            code=code,
            module=mod,
            description=desc,
            created_at=get_datetime_now(-10)
        )
        db.add(p)
        perms[code] = p
    await db.commit()

    # Re-fetch permissions to load in session
    for code in perms:
        res = await db.execute(select(Permission).filter(Permission.code == code))
        perms[code] = res.scalars().first()

    # 7. Default Tenant Roles
    role_admin = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="admin",
        description="Administrator - Full access",
        is_system=True,
        permissions=list(perms.values()),
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )

    role_pharmacist = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="pharmacist",
        description="Pharmacist - Can manage inventory and prescriptions",
        is_system=True,
        permissions=[perms[c] for c in ["view_inventory", "manage_inventory", "view_sales", "manage_sales", "view_prescriptions", "manage_prescriptions"]],
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )

    role_cashier = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="cashier",
        description="Cashier - Can perform sales transactions",
        is_system=True,
        permissions=[perms[c] for c in ["view_inventory", "view_sales", "manage_sales", "view_prescriptions"]],
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )

    role_manager = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="manager",
        description="Store Manager - Can view reports and manage store operations",
        is_system=True,
        permissions=[perms[c] for c in ["view_inventory", "manage_inventory", "view_sales", "manage_sales", "view_reports", "view_prescriptions", "manage_prescriptions"]],
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(-10)
    )

    db.add_all([role_admin, role_pharmacist, role_cashier, role_manager])
    await db.commit()
    await db.refresh(role_admin)

    # 8. Default Administrator Staff User
    admin_password = "admin"
    hashed_pwd = hash_password(admin_password)
    
    admin_staff = Staff(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Administrator",
        email="admin@pharmacy.com",
        password_hash=hashed_pwd,
        status="active",
        shift="morning",
        avatar_url=None,
        joined_at=get_datetime_now(-10),
        last_seen_at=get_datetime_now(0),
        created_at=get_datetime_now(-10),
        updated_at=get_datetime_now(0)
    )
    admin_staff.roles.append(role_admin)
    db.add(admin_staff)
    await db.commit()

    print("=" * 60)
    print("CORE SEEDING COMPLETED SUCCESSFULLY!")
    print(f"Default Tenant: {tenant.name} ({tenant.slug})")
    print(f"Default Branch: {branch.name}")
    print(f"Admin Login Email: {admin_staff.email}")
    print(f"Admin Login Password: {admin_password}")
    print("=" * 60)

async def async_main():
    async with AsyncSessionLocal() as session:
        await seed_core_data(session)

def main():
    # Step 1: Create DB if not exists
    init_db_if_not_exists()
    
    # Step 2: Run Alembic migrations
    run_migrations()
    
    # Step 3: Run asynchronous core data seeding
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
