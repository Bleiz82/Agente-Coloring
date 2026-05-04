"""RQ worker setup: listens on kdp_publish and amazon_scrape queues."""

from __future__ import annotations

import os
import signal

import redis
from loguru import logger
from rq import Queue, Worker

_REDIS_URL = os.getenv("REDIS_URL", "redis://:colorforge_dev@localhost:6379/0")

QUEUE_PUBLISH = "kdp_publish"
QUEUE_SCRAPE = "amazon_scrape"


def get_redis_conn() -> redis.Redis:
    return redis.from_url(_REDIS_URL)


def run_worker(burst: bool = False) -> None:
    conn = get_redis_conn()
    queues = [Queue(QUEUE_PUBLISH, connection=conn), Queue(QUEUE_SCRAPE, connection=conn)]
    worker = Worker(queues, connection=conn)

    def _handle_sigterm(_sig: int, _frame: object) -> None:
        logger.info("SIGTERM received, stopping worker gracefully")
        worker.stop_executing_job()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)
    logger.info("worker starting, queues={}", [q.name for q in queues])
    worker.work(burst=burst, with_scheduler=False)


__all__ = ["get_redis_conn", "run_worker", "QUEUE_PUBLISH", "QUEUE_SCRAPE"]
