import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin
import enum
from datetime import datetime
from models.user import User



class Session(Base,TimestampMixin):
    __tablename__='sessions'


    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('users.id',ondelete="CASCADE"),nullable=False,index=True)
    refresh_token_hash:Mapped[str]=mapped_column(String,nullable=True)
    device_info:Mapped[str|None] = mapped_column(String, nullable=True)
    ip: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)



    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)



    user: Mapped["User"] = relationship("User", back_populates="sessions")