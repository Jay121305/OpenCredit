import logging

from redis import Redis

from app.core.config import settings


logger = logging.getLogger(__name__)


def run_worker() -> None:
    logger.info("Analytics worker started")
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    last_id = "$"

    while True:
        result = redis_client.xread({settings.stream_name: last_id}, count=100, block=5000)
        if not result:
            continue
        for _, events in result:
            for event_id, payload in events:
                last_id = event_id
                logger.info("Consumed transaction event: %s", payload)


if __name__ == "__main__":
    run_worker()
