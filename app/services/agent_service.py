from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.agent import Agent, AgentStatusEnum
from app.schemas.agent import AgentCreate, AgentUpdate
from app.crud.crud_agent import crud_agent


class AgentService:
    @staticmethod
    def create_agent(db: Session, agent_in: AgentCreate) -> Agent:
        return crud_agent.create(db, agent_in=agent_in)

    @staticmethod
    def get_agent_by_id(db: Session, agent_id: int) -> Optional[Agent]:
        return crud_agent.get_by_id(db, agent_id=agent_id)

    @staticmethod
    def get_agent_by_email(db: Session, email: str) -> Optional[Agent]:
        return crud_agent.get_by_email(db, email=email)

    @staticmethod
    def get_all_agents(
        db: Session, skip: int = 0, limit: int = 100
    ) -> List[Agent]:
        return crud_agent.get_all(db, skip=skip, limit=limit)

    @staticmethod
    def update_agent(
        db: Session, agent_id: int, agent_in: AgentUpdate
    ) -> Optional[Agent]:
        return crud_agent.update(db, agent_id=agent_id, agent_in=agent_in)

    @staticmethod
    def update_agent_status(
        db: Session, agent_id: int, status: AgentStatusEnum
    ) -> Optional[Agent]:
        return crud_agent.update_status(db, agent_id=agent_id, new_status=status)

    @staticmethod
    def release_agent_from_hold(db: Session, agent_id: int) -> bool:
        agent = crud_agent.get_by_id(db, agent_id=agent_id)
        if not agent:
            return False

        if agent.status == AgentStatusEnum.ON_HOLD:
            crud_agent.update_status(db, agent_id=agent.id, new_status=AgentStatusEnum.AVAILABLE)
            return True

        return False
