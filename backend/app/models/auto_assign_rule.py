from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AutoAssignRule(Base):
    __tablename__ = "auto_assign_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    counterpart: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    budget_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("budgets.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    category: Mapped[Optional["Category"]] = relationship(
        back_populates="auto_assign_rules"
    )
    budget: Mapped[Optional["Budget"]] = relationship(
        back_populates="auto_assign_rules"
    )
