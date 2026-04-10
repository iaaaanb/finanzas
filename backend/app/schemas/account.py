from datetime import datetime
from pydantic import BaseModel


class AccountCreate(BaseModel):
    name: str
    bank: str
    color: str
    balance: int = 0


class AccountUpdate(BaseModel):
    name: str | None = None
    bank: str | None = None
    color: str | None = None
    balance: int | None = None


class AccountRead(BaseModel):
    id: int
    name: str
    bank: str
    color: str
    balance: int
    created_at: datetime

    model_config = {"from_attributes": True}
