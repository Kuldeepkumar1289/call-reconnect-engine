from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.agent import AgentStatusEnum
from app.models.call import CallStatusEnum, DisconnectReasonEnum
from app.core.redis import RedisSessionManager
from app.crud.crud_agent import crud_agent
from app.crud.crud_call import crud_call
from app.schemas.call import (
    InboundCallRequest,
    CallDisconnectRequest,
    CallRoutingResponse,
    CallCompleteRequest,
)


class CallService:
    @staticmethod
    def route_inbound_call(db: Session, request: InboundCallRequest) -> CallRoutingResponse:
        customer_phone = request.customer_phone_number
        session_id = request.call_session_id

        # 1. Idempotency Check via CRUD
        existing_call = crud_call.get_by_session_id(db, session_id=session_id)
        if existing_call:
            agent = (
                crud_agent.get_by_id(db, agent_id=existing_call.assigned_agent_id)
                if existing_call.assigned_agent_id
                else None
            )
            return CallRoutingResponse(
                call_session_id=existing_call.call_session_id,
                customer_phone_number=existing_call.customer_phone_number,
                assigned_agent_id=existing_call.assigned_agent_id or 0,
                assigned_agent_code=agent.agent_code if agent else "UNASSIGNED",
                is_reconnected=bool(existing_call.is_reconnected_call),
                previous_call_id=existing_call.previous_call_id,
                routing_message="Returning existing call session (Idempotent replay)",
            )

        # 2. Redis Sticky Session Check
        cached_drop = RedisSessionManager.get_dropped_call_session(customer_phone)

        if cached_drop:
            agent_id = cached_drop["agent_id"]
            original_call_id = cached_drop["original_call_id"]

            agent = crud_agent.get_by_id(db, agent_id=agent_id)
            if agent:
                agent.status = AgentStatusEnum.BUSY

                reconnected_call = crud_call.create_call(
                    db=db,
                    call_session_id=session_id,
                    customer_phone_number=customer_phone,
                    assigned_agent_id=agent.id,
                    call_status=CallStatusEnum.IN_PROGRESS,
                    is_reconnected_call=1,
                    previous_call_id=original_call_id,
                    started_at=datetime.now(timezone.utc),
                )

                drop_log = crud_call.get_pending_drop_by_original_call(db, original_call_id=original_call_id)
                if drop_log:
                    crud_call.mark_drop_as_reconnected(db, drop_log=drop_log)

                RedisSessionManager.clear_dropped_session(customer_phone)
                db.commit()

                return CallRoutingResponse(
                    call_session_id=session_id,
                    customer_phone_number=customer_phone,
                    assigned_agent_id=agent.id,
                    assigned_agent_code=agent.agent_code,
                    is_reconnected=True,
                    previous_call_id=original_call_id,
                    routing_message="Reconnected to previous agent within window.",
                )

        # 3. Standard Inbound Routing
        available_agent = crud_agent.get_available_agent_for_routing(db)

        assigned_agent_id: Optional[int] = None
        assigned_agent_code: str = "UNASSIGNED"
        call_status = CallStatusEnum.QUEUED

        if available_agent:
            available_agent.status = AgentStatusEnum.BUSY
            assigned_agent_id = available_agent.id
            assigned_agent_code = available_agent.agent_code
            call_status = CallStatusEnum.IN_PROGRESS

        new_call = crud_call.create_call(
            db=db,
            call_session_id=session_id,
            customer_phone_number=customer_phone,
            assigned_agent_id=assigned_agent_id,
            call_status=call_status,
            is_reconnected_call=0,
            previous_call_id=None,
            started_at=datetime.now(timezone.utc) if available_agent else None,
        )

        return CallRoutingResponse(
            call_session_id=session_id,
            customer_phone_number=customer_phone,
            assigned_agent_id=assigned_agent_id or 0,
            assigned_agent_code=assigned_agent_code,
            is_reconnected=False,
            previous_call_id=None,
            routing_message="Fresh call processed via standard routing" if available_agent else "No agent available; call queued",
        )

    @staticmethod
    def handle_call_disconnect(db: Session, request: CallDisconnectRequest) -> dict:
        call = crud_call.get_by_session_id(db, session_id=request.call_session_id)
        if not call:
            return {"success": False, "error": "Call not found"}

        now_utc = datetime.now(timezone.utc)
        call.ended_at = now_utc
        call.disconnect_reason = request.disconnect_reason

        agent = crud_agent.get_by_id(db, agent_id=call.assigned_agent_id) if call.assigned_agent_id else None

        if request.disconnect_reason == DisconnectReasonEnum.NETWORK_FAILURE and agent:
            call.call_status = CallStatusEnum.DROPPED
            agent.status = AgentStatusEnum.ON_HOLD

            RedisSessionManager.set_dropped_call_session(
                customer_phone=call.customer_phone_number,
                agent_id=agent.id,
                original_call_id=call.id,
            )

            expires_at = now_utc + timedelta(seconds=settings.STICKY_WINDOW_SECONDS)
            crud_call.create_drop_log(
                db=db,
                original_call_id=call.id,
                customer_phone_number=call.customer_phone_number,
                assigned_agent_id=agent.id,
                expires_at=expires_at,
            )

            return {
                "success": True,
                "call_session_id": call.call_session_id,
                "status": "DROPPED",
                "sticky_reconnect_window_active": True,
                "agent_status": "ON_HOLD",
            }

        call.call_status = CallStatusEnum.COMPLETED
        if agent:
            agent.status = AgentStatusEnum.AVAILABLE

        db.commit()

        return {
            "success": True,
            "call_session_id": call.call_session_id,
            "status": "COMPLETED",
            "sticky_reconnect_window_active": False,
            "agent_status": "AVAILABLE" if agent else None,
        }

    @staticmethod
    def complete_call(db: Session, request: CallCompleteRequest) -> dict:
        call = crud_call.get_by_session_id(db, session_id=request.call_session_id)
        if not call:
            return {"success": False, "error": "Call session not found"}

        if call.call_status == CallStatusEnum.COMPLETED:
            return {
                "success": True,
                "call_session_id": call.call_session_id,
                "status": "COMPLETED",
                "message": "Call session already marked as completed.",
            }

        now_utc = datetime.now(timezone.utc)
        call.call_status = CallStatusEnum.COMPLETED
        call.ended_at = now_utc

        if hasattr(call, "duration_seconds") and request.call_duration_seconds is not None:
            call.duration_seconds = request.call_duration_seconds

        agent = (
            crud_agent.get_by_id(db, agent_id=call.assigned_agent_id)
            if call.assigned_agent_id
            else None
        )
        if agent:
            agent.status = AgentStatusEnum.AVAILABLE

        RedisSessionManager.clear_dropped_session(call.customer_phone_number)
        db.commit()

        return {
            "success": True,
            "call_session_id": call.call_session_id,
            "customer_phone_number": call.customer_phone_number,
            "status": "COMPLETED",
            "agent_code": agent.agent_code if agent else "UNASSIGNED",
            "agent_status": agent.status.value if agent else None,
            "message": "Call completed successfully and agent is now AVAILABLE.",
        }
