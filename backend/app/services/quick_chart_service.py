"""
快速图表服务：清理缓存、按配置预计算并写入缓存、按 key 读取缓存。
"""
import logging
from typing import Optional
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.quick_chart_config import QUICK_CHART_PRECOMPUTE_URLS
from app.models.quick_chart_cache import QuickChartCache

def _internal_headers():
    secret = getattr(settings, "QUICK_CHART_INTERNAL_SECRET", None)
    if secret:
        return {"X-Quick-Chart-Secret": secret}
    return {}

logger = logging.getLogger(__name__)

# 预计算时请求 base URL（本地）
BASE_URL = "http://127.0.0.1:8000"


def build_cache_key(path: str, query_string: str) -> str:
    """path + 排序后的 query 构成唯一 key（不含 ? 时 query_string 可为空）"""
    if not query_string or query_string == "?":
        return path
    # 归一化：按 key 排序
    parts = []
    for part in query_string.strip("?").split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            parts.append((k, v))
    parts.sort(key=lambda x: x[0])
    normalized = urlencode(parts)
    return f"{path}?{normalized}" if normalized else path


def get_cached(db: Session, cache_key: str) -> Optional[str]:
    """返回缓存的 response_body（JSON 字符串），未命中返回 None"""
    row = db.query(QuickChartCache).filter(QuickChartCache.cache_key == cache_key).first()
    if not row:
        return None
    return row.response_body


def set_cached(db: Session, cache_key: str, response_body: str) -> None:
    """写入或覆盖一条缓存"""
    row = db.query(QuickChartCache).filter(QuickChartCache.cache_key == cache_key).first()
    if row:
        row.response_body = response_body
    else:
        db.add(QuickChartCache(cache_key=cache_key, response_body=response_body))
    db.commit()


def clear_all_cached(db: Session) -> int:
    """清空所有快速图表缓存，返回删除条数"""
    n = db.query(QuickChartCache).delete()
    db.commit()
    return n


def regenerate_cache_sync(db: Session) -> dict:
    """
    同步预计算：清空缓存后按 QUICK_CHART_PRECOMPUTE_URLS 请求并写入缓存。
    使用 httpx 请求本地 BASE_URL，需在进程内调用（无 auth 时可请求无需登录的接口）。
    返回 {"cleared": n, "computed": k, "errors": [...]}。
    """
    import httpx

    cleared = clear_all_cached(db)
    computed = 0
    errors = []
    base = getattr(settings, "BACKEND_BASE_URL", None) or BASE_URL
    timeout = 120.0

    for item in QUICK_CHART_PRECOMPUTE_URLS:
        path = item["path"]
        params = item.get("params") or {}
        cache_key = build_cache_key(path, urlencode(params) if params else "")
        try:
            with httpx.Client(base_url=base, timeout=timeout) as client:
                r = client.get(path, params=params, headers=_internal_headers())
                r.raise_for_status()
                body = r.text
            set_cached(db, cache_key, body)
            computed += 1
        except Exception as e:
            errors.append({"path": path, "params": params, "error": str(e)})
            logger.warning("Quick chart precompute failed: %s %s %s", path, params, e)

    return {"cleared": cleared, "computed": computed, "errors": errors}
