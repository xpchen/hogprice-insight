"""
图表 API：超过 3 秒打日志；优先返回缓存，未命中则正常处理并按需预热写入缓存。
"""
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.quick_chart_config import (
    CHART_RESPONSE_SLOW_THRESHOLD_SEC,
    is_chart_api_path,
)
from app.core.database import SessionLocal
from app.services.quick_chart_service import build_cache_key, get_cached, set_cached

logger = logging.getLogger(__name__)


class ChartTimingAndCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method != "GET":
            return await call_next(request)
        path = request.url.path
        if not is_chart_api_path(path):
            return await call_next(request)

        # 审计对账模式：禁用缓存，直接透传请求
        if getattr(settings, "DISABLE_CHART_CACHE", False):
            return await call_next(request)

        query_string = request.scope.get("query_string", b"").decode("utf-8")
        cache_key = build_cache_key(path, query_string)
        db = SessionLocal()
        try:
            cached = get_cached(db, cache_key)
            if cached is not None:
                if "/price-display/slaughter" in path:
                    logger.info(
                        "chart_cache_hit path=%s query=%s cache_key=%s",
                        path, query_string or "(none)", cache_key
                    )
                return Response(content=cached, media_type="application/json")
        finally:
            db.close()
        if "/price-display/slaughter" in path:
            logger.info(
                "chart_cache_miss path=%s query=%s cache_key=%s",
                path, query_string or "(none)", cache_key
            )

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        if elapsed > CHART_RESPONSE_SLOW_THRESHOLD_SEC:
            logger.warning(
                "chart_api_slow path=%s query=%s elapsed_sec=%.2f",
                path,
                query_string or "(none)",
                elapsed,
            )

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        # 不缓存空的统计局季度数据（避免导入数据后仍返回旧缓存）
        should_cache = response.status_code == 200 and body
        if should_cache and "/statistics-bureau/quarterly-data" in path:
            try:
                import json
                data = json.loads(body.decode("utf-8"))
                if isinstance(data, dict) and not data.get("rows") and not data.get("header_row_0"):
                    should_cache = False
            except Exception:
                pass
        # 不缓存空的波动率（避免 API 修复后仍命中旧的空缓存）
        if should_cache and "volatility" in path:
            try:
                import json
                data = json.loads(body.decode("utf-8"))
                if isinstance(data, dict) and data.get("series") == []:
                    should_cache = False
            except Exception:
                pass
        # 不缓存空的毛白价差（避免导入新数据后仍返回旧缓存）
        if should_cache and "/live-white-spread/dual-axis" in path:
            try:
                import json
                data = json.loads(body.decode("utf-8"))
                if isinstance(data, dict) and (not data.get("spread_data") and not data.get("ratio_data")):
                    should_cache = False
            except Exception:
                pass
        if should_cache and not getattr(settings, "DISABLE_CHART_CACHE", False):
            db_write = SessionLocal()
            try:
                set_cached(db_write, cache_key, body.decode("utf-8"))
            except Exception as e:
                logger.warning("chart_cache_write_failed cache_key=%s error=%s", cache_key, e)
            finally:
                db_write.close()
        return Response(
            content=body,
            status_code=response.status_code,
            media_type=response.media_type,
        )
