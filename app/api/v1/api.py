from fastapi import APIRouter
from app.api.v1.endpoints import calls, agents, telemetry

api_router = APIRouter()

api_router.include_router(
    calls.router,
    prefix="/calls",
    tags=["Calls"]
)

api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["Agents"]
)

api_router.include_router(
    telemetry.router,
    prefix="/telemetry",
    tags=["Telemetry"]
)