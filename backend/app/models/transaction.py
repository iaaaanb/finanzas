import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Date, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TxType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class TxStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[TxType] = mapped_column(
        Enum(TxType, name="tx_type"), nullable=False
    )
    status: Mapped[TxStatus] = mapped_column(
        Enum(TxStatus, name="tx_status"), nullable=False, default=TxStatus.PENDING
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    counterpart: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    budget_period_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("budget_periods.id"), nullable=True
    )
    email_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("emails.id"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    account: Mapped["Account"] = relationship(back_populates="transactions")
    category: Mapped[Optional["Category"]] = relationship(
        back_populates="transactions"
    )
    budget_period: Mapped[Optional["BudgetPeriod"]] = relationship(
        back_populates="transactions"
    )
    email: Mapped[Optional["Email"]] = relationship(back_populates="transaction")
