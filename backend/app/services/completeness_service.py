from typing import Dict, List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from sqlalchemy.dialects.mysql import JSON

from app.models import FactObservation, DimMetric


def get_metrics_completeness(
    db: Session,
    as_of: Optional[date] = None,
    window: int = 7,
    metric_group: Optional[str] = None
) -> Dict:
    """
    获取指标完成度统计
    
    Args:
        db: 数据库会话
        as_of: 基准日期（默认：数据库最新日期）
        window: 窗口天数（默认7）
        metric_group: 指标组过滤（可选）
    
    Returns:
        {
            "as_of": "2026-02-01",
            "window": 7,
            "summary": {"total": 320, "ok": 290, "late": 30},
            "items": [
                {
                    "metric_id": 101,
                    "metric_name": "全国标猪价格",
                    "latest_date": "2026-01-31",
                    "missing_days": 0,
                    "coverage_ratio": 1.0
                }
            ]
        }
    """
    # 确定基准日期
    if as_of is None:
        latest_date_result = db.query(func.max(FactObservation.obs_date)).scalar()
        if latest_date_result is None:
            return {
                "as_of": date.today().isoformat(),
                "window": window,
                "summary": {"total": 0, "ok": 0, "late": 0},
                "items": []
            }
        as_of = latest_date_result
    
    # 计算窗口起始日期
    window_start = as_of - timedelta(days=window - 1)
    
    # 构建查询：按metric_id聚合
    query = db.query(
        FactObservation.metric_id,
        DimMetric.metric_name,
        DimMetric.metric_group,
        func.max(FactObservation.obs_date).label('latest_date'),
        func.count(func.distinct(FactObservation.obs_date)).label('present_days')
    ).join(
        DimMetric, FactObservation.metric_id == DimMetric.id
    ).filter(
        FactObservation.obs_date >= window_start,
        FactObservation.obs_date <= as_of
    )
    
    # 指标组过滤
    if metric_group:
        query = query.filter(DimMetric.metric_group == metric_group)
    
    # 分组
    query = query.group_by(
        FactObservation.metric_id,
        DimMetric.metric_name,
        DimMetric.metric_group
    )
    
    results = query.all()
    
    # 处理结果
    items = []
    ok_count = 0
    late_count = 0
    
    for row in results:
        metric_id, metric_name, metric_group, latest_date, present_days = row
        
        # 计算缺失天数
        # 如果latest_date在窗口内，missing_days = window - present_days
        # 如果latest_date在窗口外，missing_days = window（完全缺失）
        if latest_date and latest_date >= window_start:
            missing_days = window - present_days
        else:
            missing_days = window
        
        # 覆盖率
        coverage_ratio = present_days / window if window > 0 else 0.0
        
        # 判断是否及时更新（latest_date >= as_of - 1，允许1天延迟）
        is_ok = latest_date and latest_date >= (as_of - timedelta(days=1))
        
        if is_ok:
            ok_count += 1
        else:
            late_count += 1
        
        items.append({
            "metric_id": metric_id,
            "metric_name": metric_name,
            "metric_group": metric_group,
            "latest_date": latest_date.isoformat() if latest_date else None,
            "missing_days": missing_days,
            "coverage_ratio": round(coverage_ratio, 2)
        })
    
    # 按missing_days降序排序（缺失最多的在前）
    items.sort(key=lambda x: x["missing_days"], reverse=True)
    
    return {
        "as_of": as_of.isoformat(),
        "window": window,
        "summary": {
            "total": len(items),
            "ok": ok_count,
            "late": late_count
        },
        "items": items
    }
