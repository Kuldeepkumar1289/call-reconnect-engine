from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.call_service import CallService
from app.schemas.call import (
    InboundCallRequest,
    CallRoutingResponse,
    CallDisconnectRequest,
)

router = APIRouter()


@router.post(
    "/inbound",
    response_model=CallRoutingResponse,
    status_code=status.HTTP_200_OK,
)
def handle_inbound_call(
    payload: InboundCallRequest,
    db: Session = Depends(get_db),
):
    try:
        routing_result = CallService.route_inbound_call(db=db, request=payload)
        return routing_result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inbound routing failed: {str(exc)}",
        )


@router.post(
    "/disconnect",
    status_code=status.HTTP_200_OK,
)
def handle_call_disconnect(
    payload: CallDisconnectRequest,
    db: Session = Depends(get_db),
):
    result = CallService.handle_call_disconnect(db=db, request=payload)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Failed to process call disconnection"),
        )
    return result