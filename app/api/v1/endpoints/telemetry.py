from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.telemetry_service import TelemetryService

router = APIRouter()


@router.get(
    "/metrics",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
)
def get_call_system_metrics(
    db: Session = Depends(get_db),
):
    try:
        metrics = TelemetryService.get_system_metrics(db=db)
        return metrics
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch system metrics: {str(exc)}",
        )


@router.get(
    "/agents/occupancy",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
)
def get_agent_occupancy_metrics(
    db: Session = Depends(get_db),
):
    try:
        occupancy = TelemetryService.get_agent_occupancy_summary(db=db)
        return occupancy
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agent occupancy metrics: {str(exc)}",
        )