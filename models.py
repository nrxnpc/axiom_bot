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
    user_id = Column(String, unique=True, nullable=False, index=True)  # UUID из приложения
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)
    password_hash = Column(String, nullable=False)
    user_type = Column(String, default="individual")
    points = Column(Integer, default=0)
    role = Column(String, default="user")  # user, admin, operator
    registration_date = Column(TIMESTAMP, server_default=func.now())
    is_active = Column(Boolean, default=True)
    last_login = Column(TIMESTAMP)
    telegram_id = Column(Integer)

    transactions = relationship("PointTransaction", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    orders = relationship("Order", back_populates="user")
    qr_scans = relationship("AppQRScan", back_populates="user")
    tickets = relationship("SupportTicket", back_populates="user")

class Car(Base):
    __tablename__ = "cars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    price = Column(String, nullable=False)
    image_url = Column(String)
    description = Column(Text)
    engine = Column(String)
    transmission = Column(String)
    fuel_type = Column(String)
    body_type = Column(String)
    drivetrain = Column(String)
    color = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("app_users.id"))

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    points_cost = Column(Integer, nullable=False)
    image_url = Column(String)
    description = Column(Text)
    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    delivery_options = Column(JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("app_users.id"))

    orders = relationship("Order", back_populates="product")

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String)
    is_important = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    published_at = Column(TIMESTAMP)
    is_published = Column(Boolean, default=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"))
    tags = Column(JSONB)

class Lottery(Base):
    __tablename__ = "lotteries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    prize = Column(String, nullable=False)
    start_date = Column(TIMESTAMP, nullable=False)
    end_date = Column(TIMESTAMP, nullable=False)
    is_active = Column(Boolean, default=True)
    participants = Column(JSONB)  # массив user_id
    winner_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"))
    min_points_required = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    image_url = Column(String)

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    points_spent = Column(Integer, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())
    delivery_address = Column(Text)
    delivery_option = Column(String, nullable=False)
    tracking_number = Column(String)

    user = relationship("AppUser", back_populates="orders")
    product = relationship("Product", back_populates="orders")

class PriceRequest(Base):
    __tablename__ = "price_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=False)
    car_id = Column(UUID(as_uuid=True), ForeignKey("cars.id"), nullable=False)
    user_message = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())
    dealer_response = Column(Text)
    estimated_price = Column(String)
    responded_at = Column(TIMESTAMP)

class PointTransaction(Base):
    __tablename__ = "point_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=False)
    type = Column(String, nullable=False)  # earned, spent, bonus, penalty
    amount = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    related_id = Column(UUID(as_uuid=True))
    qr_scan_id = Column(UUID(as_uuid=True))

    user = relationship("AppUser", back_populates="transactions")


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

    user = relationship("AppUser", back_populates="qr_scans")

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=False)
    subject = Column(String, nullable=False)
    status = Column(String, default="open")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    priority = Column(String, default="medium")

    user = relationship("AppUser", back_populates="tickets")
    messages = relationship("SupportMessage", back_populates="ticket")

class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id"), nullable=False)
    content = Column(Text, nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=False)
    sender_role = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    attachments = Column(JSONB)

    ticket = relationship("SupportTicket", back_populates="messages")

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    expires_at = Column(TIMESTAMP, nullable=False)
    is_active = Column(Boolean, default=True)
    device_info = Column(Text)

    user = relationship("AppUser", back_populates="sessions")







