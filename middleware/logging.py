import uuid
import time
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            client_ip=request.client.host,
        )

        logger.info("request_started")

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        structlog.contextvars.bind_contextvars(
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        logger.info("request_finished")

        response.headers["X-Request-ID"] = request_id
        return response
