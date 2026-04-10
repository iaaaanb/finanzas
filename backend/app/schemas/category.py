from datetime import datetime
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    color: str


class CategoryUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class CategoryRead(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}
