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
    total_dropped_calls: int = Field(..., description="How many calls were dropped in total?")
    total_reconnected_calls: int = Field(..., description="within 180s successfully reconnect calls")
    total_expired_windows: int = Field(..., description="Those whose Windows 180shas expired")
    recovery_rate_percentage: float = Field(..., description="Overall recovery percentage (SLA)")
    average_reconnect_seconds: Optional[float] = Field(None, description="On average, in how many seconds did the customer reconnect?")

class CallDropLogResponse(CallDropLogBase):
    id: int
    dropped_at: datetime
    reconnect_window_expires_at: datetime
    reconnected_at: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)