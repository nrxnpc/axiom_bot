import uuid
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass

class QRCode(Base):
    __tablename__ = "qr_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    qr_id = Column(String, unique=True, nullable=False, index=True)
    product_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    points = Column(Integer, nullable=False)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("app_users.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())
    scanned_count = Column(Integer, default=0)
    last_scanned = Column(TIMESTAMP)
    is_used = Column(Boolean, default=False)
    used_by = Column(UUID(as_uuid=True), ForeignKey("app_users.id"))
    used_at = Column(TIMESTAMP)

class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)
    password_hash = Column(String, nullable=False)
    user_type = Column(String, default="individual")
    points = Column(Integer, default=0)
    role = Column(String, default="user")
    registration_date = Column(TIMESTAMP, server_default=func.now())
    is_active = Column(Boolean, default=True)
    last_login = Column(TIMESTAMP)
    telegram_id = Column(Integer)

class AppQRScan(Base):
    __tablename__ = "app_qr_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    qr_id = Column(UUID(as_uuid=True), ForeignKey("qr_codes.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=False)
    points_earned = Column(Integer, nullable=False)
    product_name = Column(String, nullable=False)
    product_category = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    location = Column(String)

class PointTransaction(Base):
    __tablename__ = "point_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=False)
    type = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    related_id = Column(UUID(as_uuid=True))
    qr_scan_id = Column(UUID(as_uuid=True))