import json

from redis import Redis

from app.core.config import settings


class IdempotencyStore:
    def __init__(self) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    def reserve(self, key: str) -> bool:
        return bool(self.client.set(f"idem:{key}", "PENDING", nx=True, ex=settings.idempotency_ttl_seconds))

    def store_response(self, key: str, response: dict) -> None:
        self.client.set(f"idem:{key}", json.dumps(response), ex=settings.idempotency_ttl_seconds)

    def get_response(self, key: str) -> dict | None:
        value = self.client.get(f"idem:{key}")
        if not value or value == "PENDING":
            return None
        return json.loads(value)
