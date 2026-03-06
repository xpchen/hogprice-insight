"""
内部接口：供脚本 / cron 调用，不通过 Web 使用。
使用 X-Quick-Chart-Secret 校验，无需登录。
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.quick_chart_service import regenerate_cache_sync

router = APIRouter(prefix="/api/internal", tags=["internal"])


def _verify_internal_secret(x_quick_chart_secret: str | None = Header(None, alias="X-Quick-Chart-Secret")):
    """校验内部密钥，用于刷新缓存等操作。"""
    secret = getattr(settings, "QUICK_CHART_INTERNAL_SECRET", None)
    if not secret:
        raise HTTPException(status_code=501, detail="QUICK_CHART_INTERNAL_SECRET not configured")
    if not x_quick_chart_secret or x_quick_chart_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Quick-Chart-Secret")
    return True


@router.post("/refresh-chart-cache")
def refresh_chart_cache(
    _: bool = Depends(_verify_internal_secret),
    db: Session = Depends(get_db),
):
    """
    清空并重新生成图表缓存（quick_chart_cache）。
    在后台直接更新缓存，无需通过 Web 操作。
    调用方需在请求头携带 X-Quick-Chart-Secret（与 .env 中 QUICK_CHART_INTERNAL_SECRET 一致）。
    """
    result = regenerate_cache_sync(db)
    return {
        "ok": True,
        "cleared": result["cleared"],
        "computed": result["computed"],
        "errors": result.get("errors", []),
    }
