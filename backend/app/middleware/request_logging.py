"""
请求访问日志：记录每条请求的 method、path、query、状态码、耗时。
"""
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        query_string = request.scope.get("query_string", b"").decode("utf-8")
        path = request.url.path
        method = request.method

        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        logger.info(
            "request method=%s path=%s query=%s status=%s elapsed_ms=%.0f",
            method,
            path,
            query_string or "(none)",
            status,
            elapsed_ms,
        )
        return response
