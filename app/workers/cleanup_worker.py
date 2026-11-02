import asyncio
from sqlalchemy.orm import Session
from app.core.database import DatabaseSessionLocal
from app.models.agent import AgentStatusEnum
from app.models.drop_log import ReconnectStatusEnum
from app.core.redis import RedisSessionManager
from app.crud.crud_agent import crud_agent
from app.crud.crud_call import crud_call


def process_expired_drops_sync():
    db: Session = DatabaseSessionLocal()
    try:

        pending_drops = crud_call.get_pending_drops(db)

        for drop in pending_drops:
            cached = RedisSessionManager.get_dropped_call_session(
                drop.customer_phone_number
            )


            if not cached:
                drop.status = ReconnectStatusEnum.EXPIRED


                agent = crud_agent.get_by_id(db, agent_id=drop.assigned_agent_id)
                if agent and agent.status == AgentStatusEnum.ON_HOLD:
                    crud_agent.update_status(
                        db, agent_id=agent.id, new_status=AgentStatusEnum.AVAILABLE
                    )

        db.commit()
    finally:
        db.close()


async def run_cleanup_loop(interval_seconds: int = 10):
    while True:
        try:

            await asyncio.to_thread(process_expired_drops_sync)
        except Exception as e:
            print(f"Cleanup worker error: {e}")

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    print("[*] Cleanup worker service started (Interval: 10s). Press Ctrl+C to stop.")
    try:
        asyncio.run(run_cleanup_loop(interval_seconds=10))
    except KeyboardInterrupt:
        print("\n[*] Cleanup worker gracefully stopped.")
