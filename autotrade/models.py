from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, func, Date, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


# Mypy-compliant way to define the base class
class Base(DeclarativeBase):
    pass


class TradeLog(Base):
    __tablename__ = "trade_logs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(default=func.now())
    groww_order_id: Mapped[str | None] = mapped_column(String, unique=True)
    stock: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)  # 'BUY' or 'SELL'
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    total_cost: Mapped[float] = mapped_column(Float)
    profit_loss: Mapped[float | None] = mapped_column(Float, default=0.0)
    taxes: Mapped[float | None] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)  # 'LIVE' or 'PAPER'
    status: Mapped[str] = mapped_column(String, default="EXECUTED")


class Portfolio(Base):
    __tablename__ = "portfolio"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock: Mapped[str] = mapped_column(String, unique=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    average_price: Mapped[float] = mapped_column(Float)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    entry_timestamp: Mapped[datetime] = mapped_column(default=func.now())


class DailySummary(Base):
    __tablename__ = "daily_summaries"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[datetime] = mapped_column(Date, default=func.today(), unique=True)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_taxes: Mapped[float] = mapped_column(Float, default=0.0)
    net_pnl: Mapped[float] = mapped_column(Float, default=0.0)


def create_all_tables(engine_instance):
    """Creates all tables in the database."""
    Base.metadata.create_all(bind=engine_instance)
