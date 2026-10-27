import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import BaseModel

class CallStatusEnum(str, enum.Enum):
    INITIATED = "INITIATED"      
    RINGING = "RINGING"          
    IN_PROGRESS = "IN_PROGRESS"  
    COMPLETED = "COMPLETED"      
    DROPPED = "DROPPED"

class DisconnectReasonEnum(str, enum.Enum):
    NORMAL_CLEARING = "NORMAL_CLEARING"    
    NETWORK_FAILURE = "NETWORK_FAILURE"   
    AGENT_TIMEOUT = "AGENT_TIMEOUT"       
    UNKNOWN_DROP = "UNKNOWN_DROP"        

class Call(BaseModel):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    call_session_id = Column(String(100), unique=True, index=True, nullable=False)  
    customer_phone_number = Column(String(20), index=True, nullable=False)        

    assigned_agent_id = Column(
        Integer, 
        ForeignKey("agents.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )

    call_status = Column(
        Enum(CallStatusEnum), 
        default=CallStatusEnum.INITIATED, 
        nullable=False, 
        index=True
    )
    disconnect_reason = Column(
        Enum(DisconnectReasonEnum), 
        nullable=True
    )

    is_reconnected_call = Column(Integer, default=0, nullable=False)  
    previous_call_id = Column(Integer, ForeignKey("calls.id"), nullable=True)

    created_at = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    started_at = Column(DateTime(timezone=True), nullable=True)   
    ended_at = Column(DateTime(timezone=True), nullable=True)     

    # Relationships
    agent = relationship("Agent", back_populates="calls")