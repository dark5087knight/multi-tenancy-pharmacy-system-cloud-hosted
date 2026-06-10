import os
import sys
import re
import uuid
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

try:
    from psycopg2 import OperationalError as Psycopg2OpError
except ImportError:
    Psycopg2OpError = OperationalError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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

def get_postgres_urls():
    """
    Parse database settings to construct connection strings:
    1. A sync connection string for postgres (system DB) to check/create the target DB.
    2. A sync connection string for the target DB (for checks if needed).
    3. The database name.
    """
    db_url = load_database_url()
    
    # Support standard postgresql:// URLs directly, and strip +asyncpg if present
    # to convert async strings for our synchronous SQLAlchemy connection.
    sync_url = db_url.replace("+asyncpg", "")
    
    # Match pattern: protocol://user:pass@host:port/dbname
    # and optional query params (e.g., ?sslmode=require)
    match = re.match(r"(postgresql://[^/]+)/([^?#]+)(.*)", sync_url)
    if match:
        base_url = match.group(1)
        db_name = match.group(2)
        query_params = match.group(3)
        postgres_url = f"{base_url}/postgres{query_params}"
        return postgres_url, sync_url, db_name
    else:
        raise ValueError(f"Could not parse DATABASE_URL: {db_url}")

def init_db_if_not_exists():
    """
    Check if the target database exists. If not, create it.
    """
    postgres_url, _, db_name = get_postgres_urls()
    logger.info(f"Connecting to system DB: postgres at {postgres_url}...")
    
    engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        try:
            # Query pg_database to check if database exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"))
            exists = result.scalar() is not None
            if not exists:
                logger.info(f"Database '{db_name}' does not exist. Creating...")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database '{db_name}' created successfully.")
            else:
                logger.info(f"Database '{db_name}' already exists.")
        except Exception as e:
            logger.error(f"Error checking/creating database '{db_name}': {e}")
            raise e

def create_schema_if_not_exists():
    """
    Creates tables, RLS policies, and indexes if they do not exist.
    """
    _, sync_url, _ = get_postgres_urls()
    logger.info("Checking if database schema exists...")
    engine = create_engine(sync_url)
    
    # 1. Check if database is already seeded (using a separate connection)
    schema_exists = False
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT 1 FROM plans LIMIT 1"))
            schema_exists = True
        except Exception:
            schema_exists = False

    if schema_exists:
        logger.info("Database schema already exists. Skipping creation.")
        return

    logger.info("Schema does not exist. Creating schema...")
    
    # 2. Run schema creation in a fresh transaction block
    with engine.begin() as conn:
        # Execute raw SQL directly on the DBAPI cursor to bypass SQLAlchemy parameter translation issues
        raw_conn = conn.connection.dbapi_connection
        with raw_conn.cursor() as cursor:
            # 1. Run schema DDL
            try:
                cursor.execute(SCHEMA_SQL)
                logger.info("Schema tables created successfully.")
            except Exception as e:
                logger.error(f"Error creating schema tables: {e}")
                raise e
                
            # 2. Run RLS policies
            try:
                cursor.execute(RLS_POLICIES_SQL)
                logger.info("RLS policies applied successfully.")
            except Exception as e:
                logger.error(f"Error applying RLS policies: {e}")
                raise e
                
            # 3. Run indexes
            try:
                cursor.execute(INDEXES_SQL)
                logger.info("Indexes created successfully.")
            except Exception as e:
                logger.error(f"Error creating indexes: {e}")
                raise e

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
            return "$2b$12$KwRBusBDx7A7nW/huG7PkO.foSyhkKkAsOXHlv3d7VhghS8HdG8Lm"
        raise RuntimeError("bcrypt library is required to hash custom passwords.")

def seed_core_data():
    """
    Seed minimal base data needed for a clean installation.
    """
    _, sync_url, _ = get_postgres_urls()
    logger.info(f"Connecting to database to seed core data...")
    engine = create_engine(sync_url)
    
    with engine.begin() as conn:
        # 1. Check if database is already seeded
        try:
            result = conn.execute(text("SELECT 1 FROM plans LIMIT 1"))
            if result.fetchone() is not None:
                # To be absolutely sure, check if there are actual plans inserted
                check_rows = conn.execute(text("SELECT count(*) FROM plans")).scalar()
                if check_rows > 0:
                    # Database is already seeded, but make sure the admin password hash is updated to the correct one
                    admin_password = "admin"
                    hashed_pwd = hash_password(admin_password)
                    conn.execute(
                        text("UPDATE staff SET password_hash = :hash WHERE email = 'admin@pharmacy.com'"),
                        {"hash": hashed_pwd}
                    )
                    logger.info("Database already contains seed data (plans found). Updated admin password hash. Skipping full seeding.")
                    return
        except Exception as e:
            logger.error(f"Checking plans table encountered an error: {e}")
            raise e

        logger.info("Seeding core database entities...")

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

    logger.info("=" * 60)
    logger.info("CORE SEEDING COMPLETED SUCCESSFULLY!")
    logger.info("Default Tenant: Default Pharmacy (default)")
    logger.info("Default Branch: Main Branch")
    logger.info("Admin Login Email: admin@pharmacy.com")
    logger.info(f"Admin Login Password: {admin_password}")
    logger.info("=" * 60)

def run():
    MAX_RETRIES = 10
    RETRY_DELAY = 10
    
    # -------------------------
    # STEP 1: Create DB
    # -------------------------
    db_created = False
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Attempting to create database (Attempt {attempt}/{MAX_RETRIES})...")
            init_db_if_not_exists()
            db_created = True
            break
        except (Psycopg2OpError, OperationalError, Exception) as e:
            logger.error(f"Failed to create database: {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Max retries reached. Exiting.")
                sys.exit(1)

    if not db_created:
        sys.exit(1)

    # -------------------------
    # STEP 2: Seed DB
    # -------------------------
    db_seeded = False
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Attempting to seed database (Attempt {attempt}/{MAX_RETRIES})...")
            create_schema_if_not_exists()
            seed_core_data()
            db_seeded = True
            logger.info("Database seeding process finished successfully!")
            break
        except (OperationalError, Exception) as e:
            logger.error(f"Failed to seed database: {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Max retries reached. Exiting.")
                sys.exit(1)

    if not db_seeded:
        sys.exit(1)

def main():
    run()

# =====================================================================
# EMBEDDED SQL SCHEMAS (Option 2 - Standalone execution)
# =====================================================================

SCHEMA_SQL = r"""
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Platform Plans
CREATE TABLE IF NOT EXISTS plans (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name             VARCHAR(100) NOT NULL,
    slug             VARCHAR(100) NOT NULL UNIQUE,
    description      TEXT,
    price_monthly    NUMERIC(10,2) NOT NULL DEFAULT 0,
    price_yearly     NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_users        INTEGER NOT NULL DEFAULT 5,
    max_medicines    INTEGER NOT NULL DEFAULT 1000,
    max_branches     INTEGER NOT NULL DEFAULT 1,
    features         JSONB NOT NULL DEFAULT '{}',
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tenants
CREATE TABLE IF NOT EXISTS tenants (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name             VARCHAR(255) NOT NULL,
    slug             VARCHAR(100) NOT NULL UNIQUE,
    email            VARCHAR(255) NOT NULL UNIQUE,
    phone            VARCHAR(50),
    address          TEXT,
    country          CHAR(2) NOT NULL DEFAULT 'IQ',
    timezone         VARCHAR(100) NOT NULL DEFAULT 'Asia/Baghdad',
    locale           VARCHAR(20) NOT NULL DEFAULT 'en',
    currency         CHAR(3) NOT NULL DEFAULT 'IQD',
    logo_url         TEXT,
    status           VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','cancelled','trial')),
    settings         JSONB NOT NULL DEFAULT '{}',
    plan_id          UUID NOT NULL REFERENCES plans(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at       TIMESTAMPTZ
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id          UUID NOT NULL REFERENCES plans(id),
    status           VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active','trialing','past_due','cancelled','unpaid')),
    billing_cycle    VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly','yearly')),
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end   TIMESTAMPTZ NOT NULL,
    cancelled_at         TIMESTAMPTZ,
    trial_ends_at        TIMESTAMPTZ,
    external_id          VARCHAR(255),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Permissions
CREATE TABLE IF NOT EXISTS permissions (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code             VARCHAR(100) NOT NULL UNIQUE,
    description      TEXT,
    module           VARCHAR(50) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    is_system        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

-- Role Permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id          UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id    UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Staff
CREATE TABLE IF NOT EXISTS staff (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name             VARCHAR(255) NOT NULL,
    email            VARCHAR(255) NOT NULL,
    phone            VARCHAR(50),
    password_hash    TEXT,
    status           VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','suspended')),
    shift            VARCHAR(20) NOT NULL DEFAULT 'morning' CHECK (shift IN ('morning','afternoon','night','flexible')),
    avatar_url       TEXT,
    joined_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at       TIMESTAMPTZ,
    UNIQUE (tenant_id, email)
);

-- User Roles
CREATE TABLE IF NOT EXISTS user_roles (
    staff_id         UUID NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    role_id          UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by       UUID REFERENCES staff(id),
    granted_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (staff_id, role_id)
);

-- Branches
CREATE TABLE IF NOT EXISTS branches (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name             VARCHAR(255) NOT NULL,
    address          TEXT,
    phone            VARCHAR(50),
    is_main          BOOLEAN NOT NULL DEFAULT FALSE,
    status           VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name             VARCHAR(255) NOT NULL,
    phone            VARCHAR(50) NOT NULL,
    email            VARCHAR(255),
    date_of_birth    DATE,
    gender           CHAR(1) CHECK (gender IN ('M','F','O')),
    loyalty_points   INTEGER NOT NULL DEFAULT 0 CHECK (loyalty_points >= 0),
    membership_level VARCHAR(30) NOT NULL DEFAULT 'standard' CHECK (membership_level IN ('standard','silver','gold','platinum')),
    allergies        JSONB NOT NULL DEFAULT '[]',
    insurance_provider VARCHAR(255),
    insurance_policy   VARCHAR(255),
    balance          NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_spent      NUMERIC(14,2) NOT NULL DEFAULT 0,
    visits           INTEGER NOT NULL DEFAULT 0,
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at       TIMESTAMPTZ,
    created_by       UUID REFERENCES staff(id),
    UNIQUE (tenant_id, phone)
);

-- Suppliers
CREATE TABLE IF NOT EXISTS suppliers (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name             VARCHAR(255) NOT NULL,
    company          VARCHAR(255) NOT NULL,
    email            VARCHAR(255),
    phone            VARCHAR(50),
    address          TEXT,
    rating           NUMERIC(3,2) NOT NULL DEFAULT 0 CHECK (rating >= 0 AND rating <= 5),
    outstanding_balance NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_purchased  NUMERIC(14,2) NOT NULL DEFAULT 0,
    status           VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','blacklisted')),
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at       TIMESTAMPTZ,
    created_by       UUID REFERENCES staff(id)
);

-- Medicine Categories
CREATE TABLE IF NOT EXISTS medicine_categories (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

-- Medicines
CREATE TABLE IF NOT EXISTS medicines (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id        UUID REFERENCES branches(id),
    supplier_id      UUID REFERENCES suppliers(id),
    category_id      UUID REFERENCES medicine_categories(id),
    name             VARCHAR(255) NOT NULL,
    generic_name     VARCHAR(255) NOT NULL,
    brand            VARCHAR(255) NOT NULL,
    barcode          VARCHAR(100),
    sku              VARCHAR(100),
    batch_number     VARCHAR(100),
    manufacture_date DATE,
    expiry_date      DATE NOT NULL,
    quantity         INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    unit             VARCHAR(30) NOT NULL DEFAULT 'tablet',
    purchase_price   NUMERIC(12,4) NOT NULL DEFAULT 0,
    selling_price    NUMERIC(12,4) NOT NULL DEFAULT 0,
    discount         NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (discount >= 0 AND discount <= 100),
    tax_rate         NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tax_rate >= 0),
    low_stock_threshold INTEGER NOT NULL DEFAULT 10,
    rack             VARCHAR(50),
    shelf            VARCHAR(50),
    warehouse        VARCHAR(100),
    status           VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','discontinued','recalled')),
    controlled       BOOLEAN NOT NULL DEFAULT FALSE,
    prescription_required BOOLEAN NOT NULL DEFAULT FALSE,
    is_pinned        BOOLEAN NOT NULL DEFAULT FALSE,
    description      TEXT,
    side_effects     JSONB NOT NULL DEFAULT '[]',
    interactions     JSONB NOT NULL DEFAULT '[]',
    dosage           VARCHAR(255),
    storage          VARCHAR(255),
    image_url        TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at       TIMESTAMPTZ,
    created_by       UUID REFERENCES staff(id),
    updated_by       UUID REFERENCES staff(id),
    UNIQUE (tenant_id, barcode),
    UNIQUE (tenant_id, sku)
);

-- Stock Movements
CREATE TABLE IF NOT EXISTS stock_movements (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    medicine_id      UUID NOT NULL REFERENCES medicines(id),
    movement_type    VARCHAR(30) NOT NULL CHECK (movement_type IN ('purchase','sale','adjustment','return','transfer','expiry_write_off','recall')),
    quantity_before  INTEGER NOT NULL,
    quantity_change  INTEGER NOT NULL,
    quantity_after   INTEGER NOT NULL,
    reference_id     UUID,
    reference_type   VARCHAR(50),
    notes            TEXT,
    performed_by     UUID REFERENCES staff(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Prescriptions
CREATE TABLE IF NOT EXISTS prescriptions (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id      UUID NOT NULL REFERENCES customers(id),
    doctor_name      VARCHAR(255) NOT NULL,
    doctor_license   VARCHAR(100),
    issued_at        TIMESTAMPTZ NOT NULL,
    status           VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','verified','dispensed','expired','rejected')),
    image_url        TEXT,
    notes            TEXT,
    refills_remaining INTEGER NOT NULL DEFAULT 0 CHECK (refills_remaining >= 0),
    verified_by      UUID REFERENCES staff(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by       UUID REFERENCES staff(id)
);

-- Prescription Items
CREATE TABLE IF NOT EXISTS prescription_items (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    prescription_id  UUID NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    medicine_id      UUID NOT NULL REFERENCES medicines(id),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    dosage           VARCHAR(255) NOT NULL,
    instructions     TEXT
);

-- Sales
CREATE TABLE IF NOT EXISTS sales (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id        UUID REFERENCES branches(id),
    invoice_number   VARCHAR(50) NOT NULL,
    customer_id      UUID REFERENCES customers(id),
    cashier_id       UUID NOT NULL REFERENCES staff(id),
    prescription_id  UUID REFERENCES prescriptions(id),
    subtotal         NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount         NUMERIC(14,2) NOT NULL DEFAULT 0,
    tax              NUMERIC(14,2) NOT NULL DEFAULT 0,
    total            NUMERIC(14,2) NOT NULL DEFAULT 0,
    payment_method   VARCHAR(30) NOT NULL CHECK (payment_method IN ('cash','card','insurance','wallet','credit')),
    status           VARCHAR(30) NOT NULL DEFAULT 'completed' CHECK (status IN ('draft','completed','refunded','void')),
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, invoice_number)
);

-- Sale Items
CREATE TABLE IF NOT EXISTS sale_items (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sale_id          UUID NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    medicine_id      UUID NOT NULL REFERENCES medicines(id),
    name             VARCHAR(255) NOT NULL,
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price       NUMERIC(12,4) NOT NULL,
    discount         NUMERIC(5,2) NOT NULL DEFAULT 0,
    tax_rate         NUMERIC(5,2) NOT NULL DEFAULT 0,
    line_total       NUMERIC(14,2) NOT NULL
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sale_id          UUID NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    amount           NUMERIC(14,2) NOT NULL,
    method           VARCHAR(30) NOT NULL CHECK (method IN ('cash','card','insurance','wallet','credit')),
    status           VARCHAR(20) NOT NULL DEFAULT 'completed' CHECK (status IN ('pending','completed','failed','refunded')),
    reference        VARCHAR(255),
    paid_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by       UUID REFERENCES staff(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Purchase Orders
CREATE TABLE IF NOT EXISTS purchase_orders (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    po_number        VARCHAR(50) NOT NULL,
    supplier_id      UUID NOT NULL REFERENCES suppliers(id),
    status           VARCHAR(30) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sent','partial','received','cancelled')),
    total            NUMERIC(14,2) NOT NULL DEFAULT 0,
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expected_at      TIMESTAMPTZ,
    received_at      TIMESTAMPTZ,
    created_by       UUID REFERENCES staff(id),
    approved_by      UUID REFERENCES staff(id),
    UNIQUE (tenant_id, po_number)
);

-- Purchase Order Items
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    medicine_id      UUID NOT NULL REFERENCES medicines(id),
    quantity_ordered INTEGER NOT NULL CHECK (quantity_ordered > 0),
    quantity_received INTEGER NOT NULL DEFAULT 0,
    unit_cost        NUMERIC(12,4) NOT NULL,
    line_total       NUMERIC(14,2) NOT NULL
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    staff_id         UUID REFERENCES staff(id),
    title            VARCHAR(255) NOT NULL,
    body             TEXT NOT NULL,
    category         VARCHAR(50) NOT NULL,
    priority         VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high','critical')),
    read             BOOLEAN NOT NULL DEFAULT FALSE,
    read_at          TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Activities
CREATE TABLE IF NOT EXISTS activities (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type             VARCHAR(100) NOT NULL,
    message          TEXT NOT NULL,
    actor_id         UUID REFERENCES staff(id),
    severity         VARCHAR(20) NOT NULL DEFAULT 'info' CHECK (severity IN ('debug','info','warning','error','critical')),
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id),
    actor_id         UUID REFERENCES staff(id),
    action           VARCHAR(100) NOT NULL,
    table_name       VARCHAR(100) NOT NULL,
    record_id        UUID,
    old_values       JSONB,
    new_values       JSONB,
    ip_address       INET,
    user_agent       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Updated At Trigger Function and Applications
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'plans','tenants','subscriptions','roles','staff',
        'branches','customers','suppliers','medicine_categories',
        'medicines','prescriptions','sales','purchase_orders'
    ] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_' || t || '_updated_at') THEN
            EXECUTE format(
                'CREATE TRIGGER trg_%s_updated_at
                 BEFORE UPDATE ON %I
                 FOR EACH ROW EXECUTE FUNCTION set_updated_at();',
                t, t
            );
        END IF;
    END LOOP;
END;
$$;
"""

RLS_POLICIES_SQL = r"""
-- Functions for fetching RLS context
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID
LANGUAGE sql STABLE AS $$
    SELECT current_setting('app.current_tenant_id', TRUE)::UUID;
$$;

CREATE OR REPLACE FUNCTION current_staff_id() RETURNS UUID
LANGUAGE sql STABLE AS $$
    SELECT current_setting('app.current_staff_id', TRUE)::UUID;
$$;

-- Application role setup
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pharmacy_app') THEN
        CREATE ROLE pharmacy_app LOGIN PASSWORD 'CHANGE_IN_PRODUCTION';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pharmacy_readonly') THEN
        CREATE ROLE pharmacy_readonly LOGIN PASSWORD 'CHANGE_IN_PRODUCTION';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pharmacy_admin') THEN
        CREATE ROLE pharmacy_admin BYPASSRLS LOGIN PASSWORD 'CHANGE_IN_PRODUCTION';
    END IF;
END;
$$;

-- Grant permissions
GRANT USAGE ON SCHEMA public TO pharmacy_app, pharmacy_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pharmacy_readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pharmacy_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pharmacy_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO pharmacy_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO pharmacy_admin;

-- Enable RLS
ALTER TABLE customers            ENABLE ROW LEVEL SECURITY;
ALTER TABLE medicines            ENABLE ROW LEVEL SECURITY;
ALTER TABLE medicine_categories  ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers            ENABLE ROW LEVEL SECURITY;
ALTER TABLE branches             ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff                ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles                ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles           ENABLE ROW LEVEL SECURITY;
ALTER TABLE prescriptions        ENABLE ROW LEVEL SECURITY;
ALTER TABLE prescription_items   ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales                ENABLE ROW LEVEL SECURITY;
ALTER TABLE sale_items           ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments             ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_orders      ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_movements      ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications        ENABLE ROW LEVEL SECURITY;
ALTER TABLE activities           ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions        ENABLE ROW LEVEL SECURITY;

-- Drop policies if exist helper
DO $$
DECLARE
    pol_name TEXT;
    tab_name TEXT;
BEGIN
    FOR pol_name, tab_name IN 
        VALUES 
        ('tenant_isolation_select', 'customers'), ('tenant_isolation_insert', 'customers'), ('tenant_isolation_update', 'customers'), ('tenant_isolation_delete', 'customers'),
        ('tenant_isolation_select', 'medicines'), ('tenant_isolation_insert', 'medicines'), ('tenant_isolation_update', 'medicines'), ('tenant_isolation_delete', 'medicines'),
        ('tenant_isolation_select', 'medicine_categories'), ('tenant_isolation_insert', 'medicine_categories'), ('tenant_isolation_update', 'medicine_categories'), ('tenant_isolation_delete', 'medicine_categories'),
        ('tenant_isolation_select', 'suppliers'), ('tenant_isolation_insert', 'suppliers'), ('tenant_isolation_update', 'suppliers'), ('tenant_isolation_delete', 'suppliers'),
        ('tenant_isolation_select', 'branches'), ('tenant_isolation_insert', 'branches'), ('tenant_isolation_update', 'branches'), ('tenant_isolation_delete', 'branches'),
        ('tenant_isolation_select', 'staff'), ('tenant_isolation_insert', 'staff'), ('tenant_isolation_update', 'staff'), ('tenant_isolation_delete', 'staff'),
        ('tenant_isolation_select', 'roles'), ('tenant_isolation_insert', 'roles'), ('tenant_isolation_update', 'roles'), ('tenant_isolation_delete', 'roles'),
        ('tenant_isolation_select', 'user_roles'), ('tenant_isolation_insert', 'user_roles'), ('tenant_isolation_delete', 'user_roles'),
        ('tenant_isolation_select', 'prescriptions'), ('tenant_isolation_insert', 'prescriptions'), ('tenant_isolation_update', 'prescriptions'), ('tenant_isolation_delete', 'prescriptions'),
        ('tenant_isolation_select', 'prescription_items'), ('tenant_isolation_insert', 'prescription_items'), ('tenant_isolation_update', 'prescription_items'), ('tenant_isolation_delete', 'prescription_items'),
        ('tenant_isolation_select', 'sales'), ('tenant_isolation_insert', 'sales'), ('tenant_isolation_update', 'sales'), ('tenant_isolation_delete', 'sales'),
        ('tenant_isolation_select', 'sale_items'), ('tenant_isolation_insert', 'sale_items'), ('tenant_isolation_update', 'sale_items'), ('tenant_isolation_delete', 'sale_items'),
        ('tenant_isolation_select', 'payments'), ('tenant_isolation_insert', 'payments'), ('tenant_isolation_update', 'payments'), ('tenant_isolation_delete', 'payments'),
        ('tenant_isolation_select', 'purchase_orders'), ('tenant_isolation_insert', 'purchase_orders'), ('tenant_isolation_update', 'purchase_orders'), ('tenant_isolation_delete', 'purchase_orders'),
        ('tenant_isolation_select', 'purchase_order_items'), ('tenant_isolation_insert', 'purchase_order_items'), ('tenant_isolation_update', 'purchase_order_items'), ('tenant_isolation_delete', 'purchase_order_items'),
        ('tenant_isolation_select', 'stock_movements'), ('tenant_isolation_insert', 'stock_movements'),
        ('tenant_isolation_select', 'notifications'), ('tenant_isolation_insert', 'notifications'), ('tenant_isolation_update', 'notifications'), ('tenant_isolation_delete', 'notifications'),
        ('tenant_isolation_select', 'activities'), ('tenant_isolation_insert', 'activities'),
        ('tenant_isolation_select', 'audit_logs'), ('tenant_isolation_insert', 'audit_logs'),
        ('tenant_isolation_select', 'subscriptions')
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', pol_name, tab_name);
    END LOOP;
END;
$$;

-- Isolation Policies
CREATE POLICY tenant_isolation_select ON customers FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON customers FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON customers FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON customers FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON medicines FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON medicines FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON medicines FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON medicines FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON medicine_categories FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON medicine_categories FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON medicine_categories FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON medicine_categories FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON suppliers FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON suppliers FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON suppliers FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON suppliers FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON branches FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON branches FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON branches FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON branches FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON staff FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON staff FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON staff FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON staff FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON roles FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON roles FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON roles FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON roles FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON user_roles FOR SELECT TO pharmacy_app USING (EXISTS (SELECT 1 FROM staff s WHERE s.id = user_roles.staff_id AND s.tenant_id = current_tenant_id()));
CREATE POLICY tenant_isolation_insert ON user_roles FOR INSERT TO pharmacy_app WITH CHECK (EXISTS (SELECT 1 FROM staff s WHERE s.id = user_roles.staff_id AND s.tenant_id = current_tenant_id()));
CREATE POLICY tenant_isolation_delete ON user_roles FOR DELETE TO pharmacy_app USING (EXISTS (SELECT 1 FROM staff s WHERE s.id = user_roles.staff_id AND s.tenant_id = current_tenant_id()));

CREATE POLICY tenant_isolation_select ON prescriptions FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON prescriptions FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON prescriptions FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON prescriptions FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON prescription_items FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON prescription_items FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON prescription_items FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON prescription_items FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON sales FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON sales FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON sales FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON sales FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON sale_items FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON sale_items FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON sale_items FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON sale_items FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON payments FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON payments FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON payments FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON payments FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON purchase_orders FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON purchase_orders FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON purchase_orders FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON purchase_orders FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON purchase_order_items FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON purchase_order_items FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON purchase_order_items FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON purchase_order_items FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON stock_movements FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON stock_movements FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON notifications FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id() AND (staff_id IS NULL OR staff_id = current_staff_id()));
CREATE POLICY tenant_isolation_insert ON notifications FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON notifications FOR UPDATE TO pharmacy_app USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON notifications FOR DELETE TO pharmacy_app USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON activities FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON activities FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON audit_logs FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_insert ON audit_logs FOR INSERT TO pharmacy_app WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_select ON subscriptions FOR SELECT TO pharmacy_app USING (tenant_id = current_tenant_id());
RLS_POLICIES_SQL_END"""[18:22].replace("RLS_POLICIES_SQL_END", "")

INDEXES_SQL = r"""
-- Tenants
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_slug   ON tenants (slug);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_email  ON tenants (email);
CREATE        INDEX IF NOT EXISTS idx_tenants_status ON tenants (status) WHERE deleted_at IS NULL;

-- Staff
CREATE UNIQUE INDEX IF NOT EXISTS idx_staff_tenant_email ON staff (tenant_id, email) WHERE deleted_at IS NULL;
CREATE        INDEX IF NOT EXISTS idx_staff_tenant_status ON staff (tenant_id, status);

-- Customers
CREATE        INDEX IF NOT EXISTS idx_customers_tenant           ON customers (tenant_id) WHERE deleted_at IS NULL;
CREATE        INDEX IF NOT EXISTS idx_customers_tenant_phone     ON customers (tenant_id, phone);
CREATE        INDEX IF NOT EXISTS idx_customers_tenant_email     ON customers (tenant_id, email) WHERE email IS NOT NULL;
CREATE        INDEX IF NOT EXISTS idx_customers_membership       ON customers (tenant_id, membership_level);
CREATE        INDEX IF NOT EXISTS idx_customers_name_trgm        ON customers USING gin (name gin_trgm_ops);

-- Medicines
CREATE        INDEX IF NOT EXISTS idx_medicines_tenant           ON medicines (tenant_id) WHERE deleted_at IS NULL;
CREATE        INDEX IF NOT EXISTS idx_medicines_tenant_category  ON medicines (tenant_id, category_id);
CREATE        INDEX IF NOT EXISTS idx_medicines_tenant_supplier  ON medicines (tenant_id, supplier_id);
CREATE        INDEX IF NOT EXISTS idx_medicines_tenant_status    ON medicines (tenant_id, status);
CREATE        INDEX IF NOT EXISTS idx_medicines_expiry           ON medicines (tenant_id, expiry_date);
CREATE        INDEX IF NOT EXISTS idx_medicines_low_stock        ON medicines (tenant_id, quantity, low_stock_threshold) WHERE deleted_at IS NULL;
CREATE        INDEX IF NOT EXISTS idx_medicines_name_trgm        ON medicines USING gin (name gin_trgm_ops);
CREATE        INDEX IF NOT EXISTS idx_medicines_generic_trgm     ON medicines USING gin (generic_name gin_trgm_ops);

-- Stock Movements
CREATE        INDEX IF NOT EXISTS idx_stock_movements_tenant      ON stock_movements (tenant_id, created_at DESC);
CREATE        INDEX IF NOT EXISTS idx_stock_movements_medicine    ON stock_movements (medicine_id, created_at DESC);
CREATE        INDEX IF NOT EXISTS idx_stock_movements_reference   ON stock_movements (reference_type, reference_id) WHERE reference_id IS NOT NULL;

-- Sales
CREATE        INDEX IF NOT EXISTS idx_sales_tenant               ON sales (tenant_id, created_at DESC);
CREATE        INDEX IF NOT EXISTS idx_sales_tenant_customer      ON sales (tenant_id, customer_id) WHERE customer_id IS NOT NULL;
CREATE        INDEX IF NOT EXISTS idx_sales_tenant_cashier       ON sales (tenant_id, cashier_id);
CREATE        INDEX IF NOT EXISTS idx_sales_tenant_status        ON sales (tenant_id, status);
CREATE        INDEX IF NOT EXISTS idx_sales_tenant_date          ON sales (tenant_id, created_at);

-- Sale Items
CREATE        INDEX IF NOT EXISTS idx_sale_items_sale            ON sale_items (sale_id);
CREATE        INDEX IF NOT EXISTS idx_sale_items_medicine        ON sale_items (tenant_id, medicine_id);

-- Payments
CREATE        INDEX IF NOT EXISTS idx_payments_sale              ON payments (sale_id);
CREATE        INDEX IF NOT EXISTS idx_payments_tenant_date       ON payments (tenant_id, paid_at DESC);

-- Purchase Orders
CREATE        INDEX IF NOT EXISTS idx_po_tenant_status           ON purchase_orders (tenant_id, status);
CREATE        INDEX IF NOT EXISTS idx_po_tenant_supplier         ON purchase_orders (tenant_id, supplier_id);
CREATE        INDEX IF NOT EXISTS idx_po_tenant_date             ON purchase_orders (tenant_id, created_at DESC);

-- Prescriptions
CREATE        INDEX IF NOT EXISTS idx_prescriptions_tenant       ON prescriptions (tenant_id);
CREATE        INDEX IF NOT EXISTS idx_prescriptions_customer     ON prescriptions (tenant_id, customer_id);
CREATE        INDEX IF NOT EXISTS idx_prescriptions_status       ON prescriptions (tenant_id, status);

-- Notifications
CREATE        INDEX IF NOT EXISTS idx_notifications_staff_unread ON notifications (tenant_id, staff_id, read) WHERE read = FALSE;

-- Activities
CREATE        INDEX IF NOT EXISTS idx_activities_tenant_date     ON activities (tenant_id, created_at DESC);
CREATE        INDEX IF NOT EXISTS idx_activities_actor           ON activities (tenant_id, actor_id);

-- Audit Logs
CREATE        INDEX IF NOT EXISTS idx_audit_tenant_date          ON audit_logs (tenant_id, created_at DESC);
CREATE        INDEX IF NOT EXISTS idx_audit_actor                ON audit_logs (tenant_id, actor_id);
CREATE        INDEX IF NOT EXISTS idx_audit_table_record         ON audit_logs (table_name, record_id);

-- Subscriptions
CREATE        INDEX IF NOT EXISTS idx_subscriptions_tenant       ON subscriptions (tenant_id);
CREATE        INDEX IF NOT EXISTS idx_subscriptions_status       ON subscriptions (status);
CREATE        INDEX IF NOT EXISTS idx_subscriptions_period_end   ON subscriptions (current_period_end) WHERE status IN ('active','trialing','past_due');

-- Roles / RBAC
CREATE        INDEX IF NOT EXISTS idx_roles_tenant               ON roles (tenant_id);
CREATE        INDEX IF NOT EXISTS idx_user_roles_staff           ON user_roles (staff_id);
CREATE        INDEX IF NOT EXISTS idx_user_roles_role            ON user_roles (role_id);
CREATE        INDEX IF NOT EXISTS idx_role_permissions_role      ON role_permissions (role_id);
"""

if __name__ == "__main__":
    main()
