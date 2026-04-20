from datetime import datetime
from pydantic import BaseModel, model_validator


class AutoAssignRuleCreate(BaseModel):
    counterpart: str
    category_id: int | None = None
    budget_id: int | None = None
    auto_confirm: bool = False

    @model_validator(mode="after")
    def at_least_one(self):
        if (
            self.category_id is None
            and self.budget_id is None
            and not self.auto_confirm
        ):
            raise ValueError(
                "At least one of category_id, budget_id, or auto_confirm must be set"
            )
        return self


class AutoAssignRuleUpdate(BaseModel):
    category_id: int | None = None
    budget_id: int | None = None
    auto_confirm: bool | None = None


class AutoAssignRuleRead(BaseModel):
    id: int
    counterpart: str
    category_id: int | None
    budget_id: int | None
    auto_confirm: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EnableAutoConfirmResponse(BaseModel):
    """Respuesta del endpoint de activar auto-confirm: cuántas PENDING se
    confirmaron retroactivamente en el sweep."""
    rule: AutoAssignRuleRead
    retroactive_confirmed: int
    retroactive_skipped: int  # PENDING que matchearon counterpart pero sin budget/category
