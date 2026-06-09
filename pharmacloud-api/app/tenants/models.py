from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.shared.database import Base
from app.shared.base_model import TimeStampedMixin, SoftDeleteMixin

class Tenant(Base, TimeStampedMixin, SoftDeleteMixin):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(50))
    address = Column(String)
    country = Column(String(2), nullable=False, default="IQ")
    timezone = Column(String(100), nullable=False, default="Asia/Baghdad")
    locale = Column(String(20), nullable=False, default="en")
    currency = Column(String(3), nullable=False, default="IQD")
    logo_url = Column(String)
    status = Column(String(30), nullable=False, default="active")
    settings = Column(JSONB, nullable=False, default=dict)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)

    plan = relationship("Plan", back_populates="tenants")
    staff = relationship("Staff", back_populates="tenant", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="tenant", cascade="all, delete-orphan")


class Branch(Base, TimeStampedMixin):
    __tablename__ = "branches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String)
    phone = Column(String(50))
    is_main = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="active")

    tenant = relationship("Tenant", back_populates="branches")
