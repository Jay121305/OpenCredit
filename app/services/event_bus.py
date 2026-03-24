import logging

from redis import Redis

from app.core.config import settings


logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    def publish_transaction(self, payload: dict) -> None:
        try:
            self.client.xadd(
                settings.stream_name,
                payload,
                maxlen=settings.stream_max_len,
                approximate=True
            )
        except Exception:
            logger.exception("Failed to publish transaction event")
