from datetime import date as date_type, datetime
from typing import Optional
from pydantic import BaseModel

from app.models.transaction import TxType, TxStatus


class TransactionCreate(BaseModel):
    type: TxType
    amount: int
    date: date_type
    counterpart: str
    comment: Optional[str] = None
    account_id: int
    category_id: Optional[int] = None
    budget_period_id: Optional[int] = None
    remember_category: bool = False
    remember_budget: bool = False


class TransactionUpdate(BaseModel):
    amount: Optional[int] = None
    date: Optional[date_type] = None
    counterpart: Optional[str] = None
    comment: Optional[str] = None
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    budget_period_id: Optional[int] = None
    remember_category: bool = False
    remember_budget: bool = False


class TransactionRead(BaseModel):
    id: int
    type: TxType
    status: TxStatus
    amount: int
    date: date_type
    counterpart: str
    comment: Optional[str]
    account_id: int
    category_id: Optional[int]
    budget_period_id: Optional[int]
    email_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
