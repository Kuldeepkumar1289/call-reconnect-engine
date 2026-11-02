from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.agent import Agent, AgentStatusEnum
from app.schemas.agent import AgentCreate, AgentUpdate
from app.core.security import get_password_hash


class CRUDAgent:
    def get_by_id(self, db: Session, agent_id: int) -> Optional[Agent]:
        return db.query(Agent).filter(Agent.id == agent_id).first()

    def get_by_code(self, db: Session, agent_code: str) -> Optional[Agent]:
        return db.query(Agent).filter(Agent.agent_code == agent_code).first()

    def get_by_email(self, db: Session, email: str) -> Optional[Agent]:
        return db.query(Agent).filter(Agent.email == email).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[Agent]:
        return db.query(Agent).offset(skip).limit(limit).all()

    def get_available_agent_for_routing(self, db: Session) -> Optional[Agent]:
        """Locks and fetches an available active agent to prevent race conditions"""
        return (
            db.query(Agent)
            .filter(Agent.status == AgentStatusEnum.AVAILABLE, Agent.is_active == True)
            .with_for_update()
            .first()
        )

    def create(self, db: Session, agent_in: AgentCreate) -> Agent:
        db_agent = Agent(
            agent_code=agent_in.agent_code,
            full_name=agent_in.full_name,
            email=agent_in.email,
            hashed_password=get_password_hash(agent_in.password),
            status=AgentStatusEnum.AVAILABLE,
            is_active=True,
        )
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        return db_agent

    def update(self, db: Session, agent_id: int, agent_in: AgentUpdate) -> Optional[Agent]:
        agent = self.get_by_id(db, agent_id=agent_id)
        if not agent:
            return None

        update_data = agent_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(agent, field, value)

        db.commit()
        db.refresh(agent)
        return agent

    def update_status(
        self, db: Session, agent_id: int, new_status: AgentStatusEnum, commit: bool = True
    ) -> Optional[Agent]:
        agent = self.get_by_id(db, agent_id=agent_id)
        if agent:
            agent.status = new_status
            if commit:
                db.commit()
                db.refresh(agent)
        return agent

    def reset_all_to_available(self, db: Session) -> int:
        updated_count = db.query(Agent).update({Agent.status: AgentStatusEnum.AVAILABLE})
        db.commit()
        return updated_count


crud_agent = CRUDAgent()
