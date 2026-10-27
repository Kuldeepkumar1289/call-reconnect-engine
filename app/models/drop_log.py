import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from app.core.database import BaseModel

# reconnection output after drop 
class ReconnectStatusEnum(str, enum.Enum):
    PENDING = "PENDING"          
    RECONNECTED = "RECONNECTED"  
    EXPIRED = "EXPIRED"         
    FAILED = "FAILED"

class CallDropLog(BaseModel):
    __tablename__ = "call_drop_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    original_call_id = Column(Integer, ForeignKey("calls.id"), nullable=False, index=True)
    customer_phone_number = Column(String(20), index=True, nullable=False)

    assigned_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)

    dropped_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    reconnect_window_expires_at = Column(DateTime(timezone=True), nullable=False)

    status = Column(
        Enum(ReconnectStatusEnum),
        default=ReconnectStatusEnum.PENDING,
        nullable=False,
        index=True
    )
    reconnected_at = Column(DateTime(timezone=True), nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
