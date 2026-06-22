"""
Star-schema ORM models.

Design notes
------------
* dim_* tables store business dimensions.
* fact_orders is the primary fact table at order-line grain.
* fact_returns captures return and refund events.
* ingestion_audit records ingestion activity for lineage,
  monitoring, and troubleshooting.

Models are portable across SQLite (development)
and PostgreSQL (production).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financeops.db import Base


# Dimensions
class DimDate(Base):
    __tablename__ = "dim_date"

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)  # YYYYMMDD
    full_date: Mapped[dt.date] = mapped_column(Date, nullable=False, unique=True)
    day: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    month_name: Mapped[str] = mapped_column(String(12))
    quarter: Mapped[int] = mapped_column(Integer)
    year: Mapped[int] = mapped_column(Integer)
    is_weekend: Mapped[int] = mapped_column(Integer, default=0)


class DimCustomer(Base):
    __tablename__ = "dim_customer"

    customer_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    segment: Mapped[str] = mapped_column(String(20))          # Retail / SMB / Enterprise
    signup_date: Mapped[dt.date] = mapped_column(Date, nullable=True)


class DimProduct(Base):
    __tablename__ = "dim_product"

    product_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(40))
    subcategory: Mapped[str] = mapped_column(String(40))


class DimRegion(Base):
    __tablename__ = "dim_region"

    region_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    zone: Mapped[str] = mapped_column(String(20))             # North / South / East / West
    state: Mapped[str] = mapped_column(String(40))
    city: Mapped[str] = mapped_column(String(40))


# Facts
class FactOrders(Base):
    __tablename__ = "fact_orders"
    __table_args__ = (UniqueConstraint("order_id", "product_key", name="uq_order_line"),)

    order_line_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(40), index=True)
    date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"), index=True)
    customer_key: Mapped[int] = mapped_column(ForeignKey("dim_customer.customer_key"), index=True)
    product_key: Mapped[int] = mapped_column(ForeignKey("dim_product.product_key"), index=True)
    region_key: Mapped[int] = mapped_column(ForeignKey("dim_region.region_key"), index=True)

    quantity: Mapped[int] = mapped_column(Integer, default=1)
    gross_revenue: Mapped[float] = mapped_column(Float, default=0.0)   # list price * qty
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)            # COGS
    net_revenue: Mapped[float] = mapped_column(Float, default=0.0)     # gross - discount

    date = relationship("DimDate")
    customer = relationship("DimCustomer")
    product = relationship("DimProduct")
    region = relationship("DimRegion")


class FactReturns(Base):
    __tablename__ = "fact_returns"

    return_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(40), index=True)
    date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"), index=True)
    region_key: Mapped[int] = mapped_column(ForeignKey("dim_region.region_key"), index=True)
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(String(40), nullable=True)


# Operational / metadata
class IngestionAudit(Base):
    """One row per file load attempt — full data lineage."""

    __tablename__ = "ingestion_audit"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=True)
    dataset: Mapped[str] = mapped_column(String(40))          # orders | returns
    rows_received: Mapped[int] = mapped_column(Integer, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20))           # success | partial | failed
    message: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())