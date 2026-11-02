from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.call import CallStatusEnum, DisconnectReasonEnum

class CallCompleteRequest(BaseModel):
    call_session_id: str
    call_duration_seconds: Optional[int] = None

class InboundCallRequest(BaseModel):
    call_session_id: str = Field(..., min_length=5, max_length=100, examples=["CALL-UUID-98213"])
    customer_phone_number: str = Field(..., min_length=10, max_length=20, examples=["+919876543210"])


class CallDisconnectRequest(BaseModel):
    call_session_id: str = Field(..., examples=["CALL-UUID-98213"])
    disconnect_reason: DisconnectReasonEnum = Field(..., examples=[DisconnectReasonEnum.NETWORK_FAILURE])


# 3. Routing decision response schema
class CallRoutingResponse(BaseModel):
    call_session_id: str
    customer_phone_number: str
    assigned_agent_id: int
    assigned_agent_code: str
    is_reconnected: bool = Field(..., description="True if connected to previous agent, within 180s window.")
    previous_call_id: Optional[int] = None
    routing_message: str = Field(..., examples=["Reconnected to previous agent within window."])

# 4. Standard Call details response schema  
class CallResponse(BaseModel):
    id: int
    call_session_id: str
    customer_phone_number: str
    assigned_agent_id: Optional[int]
    call_status: CallStatusEnum
    disconnect_reason: Optional[DisconnectReasonEnum]
    is_reconnected_call: int
    previous_call_id: Optional[int]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)