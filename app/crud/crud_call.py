from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.call import Call, CallStatusEnum, DisconnectReasonEnum
from app.models.drop_log import CallDropLog, ReconnectStatusEnum


class CRUDCall:
    def get_by_session_id(self, db: Session, session_id: str) -> Optional[Call]:
        return db.query(Call).filter(Call.call_session_id == session_id).first()

    def create_call(
        self,
        db: Session,
        call_session_id: str,
        customer_phone_number: str,
        assigned_agent_id: Optional[int] = None,
        call_status: CallStatusEnum = CallStatusEnum.QUEUED,
        is_reconnected_call: int = 0,
        previous_call_id: Optional[int] = None,
        started_at: Optional[datetime] = None,
    ) -> Call:
        call = Call(
            call_session_id=call_session_id,
            customer_phone_number=customer_phone_number,
            assigned_agent_id=assigned_agent_id,
            call_status=call_status,
            is_reconnected_call=is_reconnected_call,
            previous_call_id=previous_call_id,
            started_at=started_at,
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call

    def create_drop_log(
        self,
        db: Session,
        original_call_id: int,
        customer_phone_number: str,
        assigned_agent_id: int,
        expires_at: datetime,
    ) -> CallDropLog:
        drop_log = CallDropLog(
            original_call_id=original_call_id,
            customer_phone_number=customer_phone_number,
            assigned_agent_id=assigned_agent_id,
            reconnect_window_expires_at=expires_at,
            status=ReconnectStatusEnum.PENDING,
        )
        db.add(drop_log)
        db.commit()
        db.refresh(drop_log)
        return drop_log

    def get_pending_drop_by_original_call(
        self, db: Session, original_call_id: int
    ) -> Optional[CallDropLog]:
        return (
            db.query(CallDropLog)
            .filter(
                CallDropLog.original_call_id == original_call_id,
                CallDropLog.status == ReconnectStatusEnum.PENDING,
            )
            .first()
        )

    def mark_drop_as_reconnected(
        self, db: Session, drop_log: CallDropLog
    ) -> CallDropLog:
        now_utc = datetime.now(timezone.utc)
        drop_log.status = ReconnectStatusEnum.RECONNECTED
        drop_log.reconnected_at = now_utc
        dropped_at = drop_log.dropped_at
        if dropped_at.tzinfo is None:
            dropped_at = dropped_at.replace(tzinfo=timezone.utc)
        drop_log.time_taken_seconds = int((now_utc - dropped_at).total_seconds())
        return drop_log

    def get_pending_drops(self, db: Session) -> List[CallDropLog]:
        return (
            db.query(CallDropLog)
            .filter(CallDropLog.status == ReconnectStatusEnum.PENDING)
            .all()
        )


crud_call = CRUDCall()
