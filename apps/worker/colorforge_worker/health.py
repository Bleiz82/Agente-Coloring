"""Simple HTTP health endpoint for the worker process."""

from __future__ import annotations

from aiohttp import web
from loguru import logger

from colorforge_worker.worker import QUEUE_PUBLISH, QUEUE_SCRAPE, get_redis_conn


async def _health_handler(request: web.Request) -> web.Response:
    try:
        conn = get_redis_conn()
        conn.ping()
        queue_info = {
            QUEUE_PUBLISH: conn.llen(f"rq:queue:{QUEUE_PUBLISH}"),
            QUEUE_SCRAPE: conn.llen(f"rq:queue:{QUEUE_SCRAPE}"),
        }
        status = "ok"
    except Exception as exc:  # noqa: BLE001
        queue_info = {}
        status = f"redis_error: {exc}"

    return web.json_response({"status": status, "queues": queue_info})


async def start_health_server(port: int = 8001) -> None:
    app = web.Application()
    app.router.add_get("/health", _health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("health server listening on port {}", port)


__all__ = ["start_health_server"]
