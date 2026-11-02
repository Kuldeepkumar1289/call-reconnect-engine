from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.agent import AgentStatusEnum
from app.services.agent_service import AgentService
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()


@router.post(
    "/",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
):
    existing_agent = AgentService.get_agent_by_email(db=db, email=payload.email)
    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An agent with this email already exists",
        )
    return AgentService.create_agent(db=db, agent_in=payload)


@router.get(
    "/",
    response_model=List[AgentResponse],
    status_code=status.HTTP_200_OK,
)
def list_agents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return AgentService.get_all_agents(db=db, skip=skip, limit=limit)


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
)
def get_agent_details(
    agent_id: int,
    db: Session = Depends(get_db),
):
    agent = AgentService.get_agent_by_id(db=db, agent_id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
)
def update_agent_details(
    agent_id: int,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
):
    agent = AgentService.update_agent(db=db, agent_id=agent_id, agent_in=payload)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


@router.patch(
    "/{agent_id}/status",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
)
def update_agent_status(
    agent_id: int,
    new_status: AgentStatusEnum,
    db: Session = Depends(get_db),
):
    agent = AgentService.update_agent_status(db=db, agent_id=agent_id, status=new_status)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


@router.post(
    "/{agent_id}/release-hold",
    status_code=status.HTTP_200_OK,
)
def release_agent_hold(
    agent_id: int,
    db: Session = Depends(get_db),
):
    success = AgentService.release_agent_from_hold(db=db, agent_id=agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is either not found or not currently in ON_HOLD status",
        )
    return {"success": True, "message": "Agent released to AVAILABLE status"}