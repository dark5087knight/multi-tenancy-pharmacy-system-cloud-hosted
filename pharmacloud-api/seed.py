import os
import sys
import re
import uuid
import json
import subprocess
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text

def load_database_url():
    """
    Load the DATABASE_URL from the environment or by parsing the .env file.
    """
    # 1. Check OS environment variable
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
        
    # 2. Try loading from .env by looking in script directory and walking up
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        env_path = os.path.join(current_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if len(parts) == 2 and parts[0].strip() == "DATABASE_URL":
                            return parts[1].strip().strip("'\"")
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
        
    raise ValueError("Could not find DATABASE_URL in environment or .env file.")

def find_api_dir():
    """
    Find the directory containing alembic.ini by walking up from the script location.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(current_dir, "alembic.ini")):
            return current_dir
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
    return os.path.dirname(os.path.abspath(__file__))

def get_postgres_urls():
    """
    Parse database settings to construct connection strings:
    1. A sync connection string for postgres (system DB) to check/create the target DB.
    2. A sync connection string for the target DB (for checks if needed).
    3. The database name.
    """
    async_url = load_database_url()
    
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
    api_dir = find_api_dir()
    
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

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt. Fall back to pre-calculated hash if bcrypt is not installed.
    """
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except ImportError:
        # Pre-calculated bcrypt hash for 'admin'
        if password == "admin":
            return "$2b$12$Z16N4XkG3wK/1L5xIe2Hpe3QEq4bQ/e07vI7gGg4.x05WqP7/oA3u"
        raise RuntimeError("bcrypt library is required to hash custom passwords.")

def seed_core_data():
    """
    Seed minimal base data needed for a clean installation.
    """
    _, sync_url, _ = get_postgres_urls()
    print(f"Connecting to database to seed core data...")
    engine = create_engine(sync_url)
    
    with engine.begin() as conn:
        # 1. Check if database is already seeded
        try:
            result = conn.execute(text("SELECT 1 FROM plans LIMIT 1"))
            if result.fetchone() is not None:
                print("Database already contains seed data (plans found). Skipping seeding.")
                return
        except Exception as e:
            # If the plans table doesn't exist, we will let the query fail or continue
            print(f"Checking plans table encountered an error (it might not exist yet): {e}")
            raise e

        print("Seeding core database entities...")

        # 2. Platform Plans
        plan_starter_id = uuid.uuid4()
        plan_pro_id = uuid.uuid4()
        plan_enterprise_id = uuid.uuid4()
        
        plans = [
            {
                "id": plan_starter_id,
                "name": "Starter",
                "slug": "starter",
                "description": "For independent pharmacies getting started.",
                "price_monthly": 29.00,
                "price_yearly": 290.00,
                "max_users": 2,
                "max_medicines": 2000,
                "max_branches": 1,
                "features": json.dumps({"pos": True, "inventory": True, "reports": False}),
                "is_active": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
            },
            {
                "id": plan_pro_id,
                "name": "Pro",
                "slug": "pro",
                "description": "Professional multi-tenant plan with full features.",
                "price_monthly": 79.00,
                "price_yearly": 790.00,
                "max_users": 50,
                "max_medicines": 50000,
                "max_branches": 10,
                "features": json.dumps({"all": True}),
                "is_active": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
            },
            {
                "id": plan_enterprise_id,
                "name": "Enterprise",
                "slug": "enterprise",
                "description": "For multi-branch networks and chains.",
                "price_monthly": 199.00,
                "price_yearly": 1990.00,
                "max_users": 999,
                "max_medicines": 999999,
                "max_branches": 999,
                "features": json.dumps({"all": True, "sso": True, "sla": True}),
                "is_active": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
            }
        ]

        for plan in plans:
            conn.execute(
                text("""
                    INSERT INTO plans (id, name, slug, description, price_monthly, price_yearly, max_users, max_medicines, max_branches, features, is_active, created_at, updated_at)
                    VALUES (:id, :name, :slug, :description, :price_monthly, :price_yearly, :max_users, :max_medicines, :max_branches, :features, :is_active, :created_at, :updated_at)
                """),
                plan
            )

        # 3. Default Tenant
        tenant_id = uuid.uuid4()
        conn.execute(
            text("""
                INSERT INTO tenants (id, name, slug, email, phone, address, country, timezone, locale, currency, logo_url, status, settings, plan_id, created_at, updated_at, deleted_at)
                VALUES (:id, :name, :slug, :email, :phone, :address, :country, :timezone, :locale, :currency, :logo_url, :status, :settings, :plan_id, :created_at, :updated_at, :deleted_at)
            """),
            {
                "id": tenant_id,
                "name": "Default Pharmacy",
                "slug": "default",
                "email": "contact@defaultpharm.com",
                "phone": "+1 555-0100",
                "address": "100 Pharmacy Blvd",
                "country": "IQ",
                "timezone": "Asia/Baghdad",
                "locale": "en",
                "currency": "IQD",
                "logo_url": None,
                "status": "active",
                "settings": json.dumps({}),
                "plan_id": plan_pro_id,
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10),
                "deleted_at": None
            }
        )

        # 4. Default Subscription
        subscription_id = uuid.uuid4()
        conn.execute(
            text("""
                INSERT INTO subscriptions (id, tenant_id, plan_id, status, billing_cycle, current_period_start, current_period_end, cancelled_at, trial_ends_at, external_id, created_at, updated_at)
                VALUES (:id, :tenant_id, :plan_id, :status, :billing_cycle, :current_period_start, :current_period_end, :cancelled_at, :trial_ends_at, :external_id, :created_at, :updated_at)
            """),
            {
                "id": subscription_id,
                "tenant_id": tenant_id,
                "plan_id": plan_pro_id,
                "status": "active",
                "billing_cycle": "monthly",
                "current_period_start": datetime.now(timezone.utc) - timedelta(days=5),
                "current_period_end": datetime.now(timezone.utc) + timedelta(days=25),
                "cancelled_at": None,
                "trial_ends_at": None,
                "external_id": None,
                "created_at": datetime.now(timezone.utc) - timedelta(days=5),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=5)
            }
        )

        # 5. Default Branch
        branch_id = uuid.uuid4()
        conn.execute(
            text("""
                INSERT INTO branches (id, tenant_id, name, address, phone, is_main, status, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :address, :phone, :is_main, :status, :created_at, :updated_at)
            """),
            {
                "id": branch_id,
                "tenant_id": tenant_id,
                "name": "Main Branch",
                "address": "100 Pharmacy Blvd",
                "phone": "+1 555-0100",
                "is_main": True,
                "status": "active",
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
            }
        )

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
        
        perms_ids = {}
        for code, mod, desc in permissions_list:
            p_id = uuid.uuid4()
            perms_ids[code] = p_id
            conn.execute(
                text("""
                    INSERT INTO permissions (id, code, module, description, created_at)
                    VALUES (:id, :code, :module, :description, :created_at)
                """),
                {
                    "id": p_id,
                    "code": code,
                    "module": mod,
                    "description": desc,
                    "created_at": datetime.now(timezone.utc) - timedelta(days=10)
                }
            )

        # 7. Default Tenant Roles
        role_admin_id = uuid.uuid4()
        role_pharmacist_id = uuid.uuid4()
        role_cashier_id = uuid.uuid4()
        role_manager_id = uuid.uuid4()
        
        # admin role
        conn.execute(
            text("""
                INSERT INTO roles (id, tenant_id, name, description, is_system, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :description, :is_system, :created_at, :updated_at)
            """),
            {
                "id": role_admin_id,
                "tenant_id": tenant_id,
                "name": "admin",
                "description": "Administrator - Full access",
                "is_system": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
            }
        )
        for p_id in perms_ids.values():
            conn.execute(
                text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
                {"role_id": role_admin_id, "permission_id": p_id}
            )

        # pharmacist role
        conn.execute(
            text("""
                INSERT INTO roles (id, tenant_id, name, description, is_system, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :description, :is_system, :created_at, :updated_at)
            """),
            {
                "id": role_pharmacist_id,
                "tenant_id": tenant_id,
                "name": "pharmacist",
                "description": "Pharmacist - Can manage inventory and prescriptions",
                "is_system": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
            }
        )
        pharmacist_perms = ["view_inventory", "manage_inventory", "view_sales", "manage_sales", "view_prescriptions", "manage_prescriptions"]
        for code in pharmacist_perms:
            conn.execute(
                text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
                {"role_id": role_pharmacist_id, "permission_id": perms_ids[code]}
            )

        # cashier role
        conn.execute(
            text("""
                INSERT INTO roles (id, tenant_id, name, description, is_system, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :description, :is_system, :created_at, :updated_at)
            """),
            {
                "id": role_cashier_id,
                "tenant_id": tenant_id,
                "name": "cashier",
                "description": "Cashier - Can perform sales transactions",
                "is_system": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
            }
        )
        cashier_perms = ["view_inventory", "view_sales", "manage_sales", "view_prescriptions"]
        for code in cashier_perms:
            conn.execute(
                text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
                {"role_id": role_cashier_id, "permission_id": perms_ids[code]}
            )

        # manager role
        conn.execute(
            text("""
                INSERT INTO roles (id, tenant_id, name, description, is_system, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :description, :is_system, :created_at, :updated_at)
            """),
            {
                "id": role_manager_id,
                "tenant_id": tenant_id,
                "name": "manager",
                "description": "Store Manager - Can view reports and manage store operations",
                "is_system": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
            }
        )
        manager_perms = ["view_inventory", "manage_inventory", "view_sales", "manage_sales", "view_reports", "view_prescriptions", "manage_prescriptions"]
        for code in manager_perms:
            conn.execute(
                text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
                {"role_id": role_manager_id, "permission_id": perms_ids[code]}
            )

        # 8. Default Administrator Staff User
        admin_password = "admin"
        hashed_pwd = hash_password(admin_password)
        admin_staff_id = uuid.uuid4()
        
        conn.execute(
            text("""
                INSERT INTO staff (id, tenant_id, name, email, phone, password_hash, status, shift, avatar_url, joined_at, last_seen_at, created_at, updated_at, deleted_at)
                VALUES (:id, :tenant_id, :name, :email, :phone, :password_hash, :status, :shift, :avatar_url, :joined_at, :last_seen_at, :created_at, :updated_at, :deleted_at)
            """),
            {
                "id": admin_staff_id,
                "tenant_id": tenant_id,
                "name": "Administrator",
                "email": "admin@pharmacy.com",
                "phone": None,
                "password_hash": hashed_pwd,
                "status": "active",
                "shift": "morning",
                "avatar_url": None,
                "joined_at": datetime.now(timezone.utc) - timedelta(days=10),
                "last_seen_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc) - timedelta(days=10),
                "updated_at": datetime.now(timezone.utc),
                "deleted_at": None
            }
        )

        # 9. Admin role assignment in user_roles
        conn.execute(
            text("""
                INSERT INTO user_roles (staff_id, role_id, granted_by, granted_at)
                VALUES (:staff_id, :role_id, :granted_by, :granted_at)
            """),
            {
                "staff_id": admin_staff_id,
                "role_id": role_admin_id,
                "granted_by": None,
                "granted_at": datetime.now(timezone.utc)
            }
        )

    print("=" * 60)
    print("CORE SEEDING COMPLETED SUCCESSFULLY!")
    print(f"Default Tenant: Default Pharmacy (default)")
    print(f"Default Branch: Main Branch")
    print(f"Admin Login Email: admin@pharmacy.com")
    print(f"Admin Login Password: {admin_password}")
    print("=" * 60)

def main():
    # Step 1: Create DB if not exists
    init_db_if_not_exists()
    
    # Step 2: Run Alembic migrations
    run_migrations()
    
    # Step 3: Run core data seeding synchronously
    seed_core_data()

if __name__ == "__main__":
    main()
