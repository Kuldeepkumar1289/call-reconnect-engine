from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.agent import AgentStatusEnum

class AgentBase(BaseModel):
    agent_code: str = Field(..., min_length=2, max_length=50, examples=["AGT-101"])
    full_name: str = Field(..., min_length=2, max_length=100, examples=["Rahul Sharma"])
    email: EmailStr = Field(..., examples=["rahul.sharma@example.com"])

class AgentCreate(AgentBase):
    password: str = Field(..., min_length=6, max_length=128, description="Plain text password which will be hashed before storing in the database")

class AgentStatusUpdate(BaseModel):
    status: AgentStatusEnum = Field(..., description="New telephony status of the agent")

class AgentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    status: Optional[AgentStatusEnum] = None

class AgentLogin(BaseModel):
    email: EmailStr
    password: str

class AgentResponse(AgentBase):
    id: int
    status: AgentStatusEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)