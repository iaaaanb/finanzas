from datetime import datetime
from pydantic import BaseModel


class AccountCreate(BaseModel):
    name: str
    bank: str
    color: str
    balance: int = 0
    account_number: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    bank: str | None = None
    color: str | None = None
    balance: int | None = None
    account_number: str | None = None


class AccountRead(BaseModel):
    id: int
    name: str
    bank: str
    color: str
    balance: int
    account_number: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
