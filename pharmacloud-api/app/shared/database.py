from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

# Create async engine. Pool pre-ping checks connections.
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

# Async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

from sqlalchemy import text

async def get_db():
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            try:
                # Reset the role and clear session variables to prevent leakage in connection pooling
                await session.execute(text("RESET ROLE"))
                await session.execute(text("SELECT set_config('app.current_tenant_id', NULL, FALSE)"))
                await session.execute(text("SELECT set_config('app.current_staff_id', NULL, FALSE)"))
                await session.commit()
            except Exception:
                pass
            await session.close()
