from datetime import datetime
from pydantic import BaseModel, model_validator


class AutoAssignRuleCreate(BaseModel):
    counterpart: str
    category_id: int | None = None
    budget_id: int | None = None

    @model_validator(mode="after")
    def at_least_one(self):
        if self.category_id is None and self.budget_id is None:
            raise ValueError("At least one of category_id or budget_id must be set")
        return self


class AutoAssignRuleUpdate(BaseModel):
    category_id: int | None = None
    budget_id: int | None = None


class AutoAssignRuleRead(BaseModel):
    id: int
    counterpart: str
    category_id: int | None
    budget_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
