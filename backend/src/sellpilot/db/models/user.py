from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import UserRole
from sellpilot.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from sellpilot.db.models.agent_task import AgentTask
    from sellpilot.db.models.confirmation_task import ConfirmationTask
    from sellpilot.db.models.operation_log import OperationLog


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default=UserRole.ADMIN, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_tasks: Mapped[list["AgentTask"]] = relationship(
        back_populates="creator", foreign_keys="AgentTask.created_by"
    )
    created_confirmations: Mapped[list["ConfirmationTask"]] = relationship(
        back_populates="creator", foreign_keys="ConfirmationTask.created_by"
    )
    confirmed_confirmations: Mapped[list["ConfirmationTask"]] = relationship(
        back_populates="confirmer", foreign_keys="ConfirmationTask.confirmed_by"
    )
    operation_logs: Mapped[list["OperationLog"]] = relationship(
        back_populates="actor", foreign_keys="OperationLog.actor_id"
    )
