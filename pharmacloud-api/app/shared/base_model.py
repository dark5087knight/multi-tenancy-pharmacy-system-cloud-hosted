import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

class TimeStampedMixin:
    """Mixin to add created_at and updated_at to models."""
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class SoftDeleteMixin:
    """Mixin to add deleted_at to models."""
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class TenantScopedMixin:
    """Mixin for tenant-scoped resources."""
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
