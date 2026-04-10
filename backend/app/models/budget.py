import enum
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BudgetType(str, enum.Enum):
    L_V = "L_V"
    V_D = "V_D"
    L_D = "L_D"
    MONTHLY = "MONTHLY"


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[BudgetType] = mapped_column(
        Enum(BudgetType, name="budget_type"), nullable=False
    )
    color: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    periods: Mapped[list["BudgetPeriod"]] = relationship(back_populates="budget")
    auto_assign_rules: Mapped[list["AutoAssignRule"]] = relationship(
        back_populates="budget"
    )
