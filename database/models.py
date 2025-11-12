"""Database models for Yandex Market Discount Bot."""
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Category(Base):
    """Product category model."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    yandex_category_id = Column(String(100))  # Yandex Market category ID
    url_path = Column(String(500))  # Category URL path
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', active={self.is_active})>"


class Product(Base):
    """Product model."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(500), nullable=False)
    yandex_product_id = Column(String(100), unique=True)  # Unique product ID from Yandex
    url = Column(Text, nullable=False)
    image_url = Column(Text)
    current_price = Column(Float, nullable=False)
    previous_price = Column(Float)
    discount_percentage = Column(Float, default=0)
    rating = Column(Float)
    reviews_count = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    last_checked = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("yandex_product_id", name="uq_yandex_product_id"),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name[:30]}...', price={self.current_price})>"


class PriceHistory(Base):
    """Price history model."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    price = Column(Float, nullable=False)
    discount_percentage = Column(Float, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory(product_id={self.product_id}, price={self.price}, date={self.recorded_at})>"


class BotSettings(Base):
    """Bot settings model."""

    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<BotSettings(key='{self.key}', value='{self.value}')>"
