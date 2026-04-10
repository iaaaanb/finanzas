from datetime import date, datetime
from typing import Optional

from sqlalchemy import Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BudgetPeriod(Base):
    __tablename__ = "budget_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.id"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    starting_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance: Mapped[int] = mapped_column(Integer, nullable=False)
    final_balance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    budget: Mapped["Budget"] = relationship(back_populates="periods")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="budget_period"
    )
