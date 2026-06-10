import os
import sys
import re
from sqlalchemy import create_engine, text

def load_database_url():
    """
    Load the DATABASE_URL from the environment or by parsing the .env file.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
        
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

def list_users():
    print("=========================================================")
    print("                PharmaCloud Database Users               ")
    print("=========================================================")
    
    try:
        raw_url = load_database_url()
        sync_url = raw_url.replace("+asyncpg", "")
        engine = create_engine(sync_url)
    except Exception as e:
        print(f"[Error] Configuration Error: Could not load database URL from .env: {e}")
        sys.exit(1)

    try:
        with engine.connect() as conn:
            # Query all staff members, their tenant, roles, and password hash
            query = text("""
                SELECT 
                    s.name as staff_name,
                    s.email as staff_email,
                    s.password_hash as pwd_hash,
                    s.status as staff_status,
                    s.shift as staff_shift,
                    t.name as tenant_name,
                    COALESCE(string_agg(r.name, ', '), 'No Roles') as roles
                FROM staff s
                JOIN tenants t ON s.tenant_id = t.id
                LEFT JOIN user_roles ur ON s.id = ur.staff_id
                LEFT JOIN roles r ON ur.role_id = r.id
                WHERE s.deleted_at IS NULL
                GROUP BY s.id, s.name, s.email, s.password_hash, s.status, s.shift, t.name
                ORDER BY t.name, s.name
            """)
            
            results = conn.execute(query).fetchall()
            
            if not results:
                print("\nNo staff members found in the database.")
                return

            print(f"\nFound {len(results)} active staff member(s):\n")
            
            # Print a neat text list for each user
            for i, row in enumerate(results, 1):
                name, email, pwd_hash, status, shift, tenant_name, roles = row
                print(f"{i}. User: {name}")
                print(f"   Email:         {email}")
                print(f"   Roles:         {roles}")
                print(f"   Status/Shift:  {status} ({shift} shift)")
                print(f"   Tenant:        {tenant_name}")
                print(f"   Password Hash: {pwd_hash}")
                print("-" * 57)
            print()

    except Exception as e:
        print(f"\n[Error] Database Error: Could not connect or query: {e}")
        sys.exit(1)

if __name__ == "__main__":
    list_users()
