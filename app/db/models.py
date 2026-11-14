# ReturnDesk - database models
"""Tables for the synthetic shop, claims, decisions and the audit trail.

Money is stored as Numeric(10, 2) in pounds sterling. Enumerated values are
stored as plain strings with CHECK constraints (native_enum=False), which keeps
migrations portable between Postgres and the SQLite used in tests.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(str, Enum):
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURNED = "returned"


class ClaimStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class Outcome(str, Enum):
    REFUND = "refund"
    REJECT = "reject"
    ESCALATE = "escalate"


class DecidedBy(str, Enum):
    RULES = "rules"
    AGENT = "agent"
    HUMAN = "human"


def _enum(enum_cls: type[Enum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
        length=20,
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    city: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Ground-truth flag used only by the synthetic data and the benchmark
    is_repeat_claimer: Mapped[bool] = mapped_column(Boolean, default=False)

    orders: Mapped[list[Order]] = relationship(back_populates="customer")
    claims: Mapped[list[Claim]] = relationship(back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), index=True)
    price_gbp: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fragile: Mapped[bool] = mapped_column(Boolean, default=False)

    orders: Mapped[list[Order]] = relationship(back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_ref: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    order_value_gbp: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus, "order_status"))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship(back_populates="orders")
    product: Mapped[Product] = relationship(back_populates="orders")
    claims: Mapped[list[Claim]] = relationship(back_populates="order")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[ClaimStatus] = mapped_column(_enum(ClaimStatus, "claim_status"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="claims")
    customer: Mapped[Customer] = relationship(back_populates="claims")
    decisions: Mapped[list[Decision]] = relationship(back_populates="claim")


# --- decisions and audit trail (stephenoke14 · mrhills) ---


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), index=True)
    outcome: Mapped[Outcome] = mapped_column(_enum(Outcome, "outcome"))
    decided_by: Mapped[DecidedBy] = mapped_column(_enum(DecidedBy, "decided_by"))
    rule_fired: Mapped[str | None] = mapped_column(String(80))
    refund_amount_gbp: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    claim: Mapped[Claim] = relationship(back_populates="decisions")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
