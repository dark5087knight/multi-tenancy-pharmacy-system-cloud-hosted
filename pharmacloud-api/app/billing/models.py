from sqlalchemy import Column, String, Integer, Numeric, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.shared.database import Base
from app.shared.base_model import TimeStampedMixin

class Plan(Base, TimeStampedMixin):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(String)
    price_monthly = Column(Numeric(10, 2), nullable=False, default=0.00)
    price_yearly = Column(Numeric(10, 2), nullable=False, default=0.00)
    max_users = Column(Integer, nullable=False, default=5)
    max_medicines = Column(Integer, nullable=False, default=1000)
    max_branches = Column(Integer, nullable=False, default=1)
    features = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationship to Tenant (string name resolution resolves circular dependencies)
    tenants = relationship("Tenant", back_populates="plan")


class Subscription(Base, TimeStampedMixin):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    status = Column(String(30), nullable=False, default="active")
    billing_cycle = Column(String(20), nullable=False, default="monthly")
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancelled_at = Column(DateTime(timezone=True))
    trial_ends_at = Column(DateTime(timezone=True))
    external_id = Column(String(255))
