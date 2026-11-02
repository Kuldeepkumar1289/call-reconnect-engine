from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.call import Call, CallStatusEnum
from app.models.drop_log import CallDropLog, ReconnectStatusEnum
from app.models.agent import Agent, AgentStatusEnum


class TelemetryService:
    @staticmethod
    def get_system_metrics(db: Session) -> Dict[str, Any]:
        total_calls = db.query(func.count(Call.id)).scalar() or 0
        total_dropped = (
            db.query(func.count(Call.id))
            .filter(Call.call_status == CallStatusEnum.DROPPED)
            .scalar()
            or 0
        )
        total_reconnected = (
            db.query(func.count(Call.id))
            .filter(Call.is_reconnected_call == 1)
            .scalar()
            or 0
        )

        drop_rate = (
            round((total_dropped / total_calls) * 100, 2)
            if total_calls > 0
            else 0.0
        )
        reconnect_rate = (
            round((total_reconnected / total_dropped) * 100, 2)
            if total_dropped > 0
            else 0.0
        )

        avg_time = (
            db.query(func.avg(CallDropLog.time_taken_seconds))
            .filter(CallDropLog.status == ReconnectStatusEnum.RECONNECTED)
            .scalar()
        )
        avg_reconnect_seconds = round(float(avg_time), 2) if avg_time else 0.0

        return {
            "total_calls": total_calls,
            "total_dropped": total_dropped,
            "total_reconnected": total_reconnected,
            "drop_rate_percentage": drop_rate,
            "reconnect_success_rate_percentage": reconnect_rate,
            "avg_reconnection_time_seconds": avg_reconnect_seconds,
        }

    @staticmethod
    def get_agent_occupancy_summary(db: Session) -> Dict[str, Any]:
        total_agents = db.query(func.count(Agent.id)).scalar() or 0
        available_agents = (
            db.query(func.count(Agent.id))
            .filter(Agent.status == AgentStatusEnum.AVAILABLE)
            .scalar()
            or 0
        )
        busy_agents = (
            db.query(func.count(Agent.id))
            .filter(Agent.status == AgentStatusEnum.BUSY)
            .scalar()
            or 0
        )
        on_hold_agents = (
            db.query(func.count(Agent.id))
            .filter(Agent.status == AgentStatusEnum.ON_HOLD)
            .scalar()
            or 0
        )

        return {
            "total_agents": total_agents,
            "available_agents": available_agents,
            "busy_agents": busy_agents,
            "on_hold_for_reconnect": on_hold_agents,
            "occupancy_rate_percentage": (
                round(((busy_agents + on_hold_agents) / total_agents) * 100, 2)
                if total_agents > 0
                else 0.0
            ),
        }