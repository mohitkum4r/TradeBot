# domain/models/models.py
from __future__ import annotations
from sqlalchemy import Integer, String, Float, func, Date, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class TradeLog(Base):
    __tablename__ = "trade_logs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    groww_order_id: Mapped[str | None] = mapped_column(String, unique=True)
    stock: Mapped[str] = mapped_column(String, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    profit_loss: Mapped[float | None] = mapped_column(Float, default=0.0)
    taxes: Mapped[float | None] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="EXECUTED", nullable=False)


class Portfolio(Base):
    __tablename__ = "portfolio"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    entry_timestamp: Mapped[datetime] = mapped_column(
        default=func.now(), nullable=False
    )


class DailySummary(Base):
    __tablename__ = "daily_summaries"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[datetime] = mapped_column(
        Date, default=func.today(), unique=True, nullable=False
    )
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_taxes: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    net_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


def create_all_tables(engine_instance):
    Base.metadata.create_all(bind=engine_instance)
