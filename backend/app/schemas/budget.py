from datetime import date, datetime
from pydantic import BaseModel

from app.models.budget import BudgetType


class BudgetCreate(BaseModel):
    name: str
    type: BudgetType
    color: str
    amount: int


class BudgetUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    amount: int | None = None


class BudgetPeriodRead(BaseModel):
    id: int
    budget_id: int
    period_start: date
    period_end: date
    starting_amount: int
    balance: int
    final_balance: int | None
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class BudgetRead(BaseModel):
    id: int
    name: str
    type: BudgetType
    color: str
    amount: int
    created_at: datetime
    active_period: BudgetPeriodRead | None = None

    model_config = {"from_attributes": True}
