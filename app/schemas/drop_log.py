from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.drop_log import ReconnectStatusEnum

class CallDropLogBase(BaseModel):
    original_call_id: int
    customer_phone_number: str
    assigned_agent_id: int
    status: ReconnectStatusEnum = ReconnectStatusEnum.PENDING

class ReconnectTelemetryMetrics(BaseModel):
    total_dropped_calls: int = Field(..., description="Total kitni calls drop hui")
    total_reconnected_calls: int = Field(..., description="180s ke andar successfully reconnect hui calls")
    total_expired_windows: int = Field(..., description="Jinki 180s window expire ho gayi")
    recovery_rate_percentage: float = Field(..., description="Overall recovery percentage (SLA)")
    average_reconnect_seconds: Optional[float] = Field(None, description="Average kitne seconds me customer reconnect hua")

class CallDropLogResponse(CallDropLogBase):
    id: int
    dropped_at: datetime
    reconnect_window_expires_at: datetime
    reconnected_at: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)