import redis
from typing import Optional
from app.core.config import settings

redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    decode_responses=True,
)

redis_client = redis.Redis(connection_pool=redis_pool)


class RedisSessionManager:
    DROP_KEY_PREFIX = "call_drop:"
    AGENT_HOLD_PREFIX = "agent_hold:"

    @classmethod
    def set_dropped_call_session(
        cls, customer_phone: str, agent_id: int, original_call_id: int
    ) -> bool:
        key = f"{cls.DROP_KEY_PREFIX}{customer_phone}"
        value = f"{agent_id}:{original_call_id}"
        return redis_client.set(key, value, ex=settings.STICKY_WINDOW_SECONDS)

    @classmethod
    def get_dropped_call_session(cls, customer_phone: str) -> Optional[dict]:
        key = f"{cls.DROP_KEY_PREFIX}{customer_phone}"
        value = redis_client.get(key)
        if not value:
            return None

        agent_id_str, original_call_id_str = value.split(":")
        ttl_remaining = redis_client.ttl(key)

        return {
            "agent_id": int(agent_id_str),
            "original_call_id": int(original_call_id_str),
            "ttl_remaining_seconds": ttl_remaining,
        }

    @classmethod
    def clear_dropped_session(cls, customer_phone: str) -> None:
        key = f"{cls.DROP_KEY_PREFIX}{customer_phone}"
        redis_client.delete(key)

    @classmethod
    def ping(cls) -> bool:
        try:
            return redis_client.ping()
        except redis.ConnectionError:
            return False