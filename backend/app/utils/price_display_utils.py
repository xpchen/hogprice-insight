"""价格展示 API 共用工具"""
from typing import Optional, Any

from app.utils.dt_parse import parse_date


def resolve_update_time(metric: Any, latest_obs: Any) -> Optional[str]:
    """
    解析更新时间：优先使用 Excel 第4行更新时间（dim_metric.source_updated_at），否则用最新观测日期。

    Args:
        metric: DimMetric 对象，含 source_updated_at 字段
        latest_obs: 最新观测记录，含 obs_date 字段

    Returns:
        YYYY-MM-DD 或 ISO 格式字符串，无数据时返回 None
    """
    if metric and getattr(metric, "source_updated_at", None):
        parsed = parse_date(metric.source_updated_at)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
    if latest_obs and getattr(latest_obs, "obs_date", None):
        return latest_obs.obs_date.isoformat()
    return None
