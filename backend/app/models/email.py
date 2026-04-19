import enum
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EmailStatus(str, enum.Enum):
    PARSED = "PARSED"
    PENDING = "PENDING"
    SKIPPED = "SKIPPED"


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    gmail_message_id: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    sender: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus, name="email_status"),
        nullable=False,
        default=EmailStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Lista (no Optional[Transaction]): un email puede generar múltiples txs
    # (ej: transferencia entre cuentas propias)
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="email"
    )
