import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import BaseModel

class AgentStatusEnum(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ON_CALL = "BUSY"
    BUSY = "BUSY"
    ON_HOLD = "ON_HOLD"
    WRAP_UP = "WRAP_UP"
    OFFLINE = "OFFLINE"

class Agent(BaseModel):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True, nullable=False)

    agent_code = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    status = Column(Enum(AgentStatusEnum), default=AgentStatusEnum.AVAILABLE, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    calls = relationship("Call", back_populates="agent")