from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow
from app.models.enums import AccountTokenPurpose
from app.models.org import Agent, enum_col


class AccountToken(Base):
    """Enlace de un solo uso para crear o restablecer la contraseña.

    Solo se guarda el SHA-256 del enlace: quien lea la base no puede usarlo.
    """

    __tablename__ = "account_tokens"
    __table_args__ = (Index("ix_account_tokens_agent", "agent_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    purpose: Mapped[AccountTokenPurpose] = mapped_column(
        enum_col(AccountTokenPurpose, "account_token_purpose")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime)  # usado o reemplazado

    agent: Mapped[Agent] = relationship(foreign_keys=[agent_id])
