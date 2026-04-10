from datetime import datetime
from pydantic import BaseModel
from app.models.email import EmailStatus


class EmailRead(BaseModel):
    id: int
    gmail_message_id: str
    sender: str
    subject: str
    body_html: str
    received_at: datetime
    status: EmailStatus
    created_at: datetime

    model_config = {"from_attributes": True}
