"""指标查询服务（适配新数据模型）"""
from typing import Dict, List, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models import FactIndicatorTs, FactIndicatorMetrics, DimIndicator, DimRegion


def query_indicator_ts(
    db: Session,
    indicator_code: str,
    region_code: Optional[str] = None,
    freq: str = "D",
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Dict:
    """
    查询指标时序数据
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        region_code: 区域代码（可选）
        freq: 频率（D/W）
        from_date: 开始日期
        to_date: 结束日期
    
    Returns:
        {
            "indicator_code": str,
            "indicator_name": str,
            "unit": str,
            "series": List[{"date": str, "value": float}],
            "update_time": str
        }
    """
    # 获取指标信息
    indicator = db.query(DimIndicator).filter(
        DimIndicator.indicator_code == indicator_code
    ).first()
    
    if not indicator:
        return {
            "indicator_code": indicator_code,
            "error": "指标不存在"
        }
    
    # 构建查询
    query = db.query(FactIndicatorTs).filter(
        FactIndicatorTs.indicator_code == indicator_code,
        FactIndicatorTs.freq == freq
    )
    
    if region_code:
        query = query.filter(FactIndicatorTs.region_code == region_code)
    
    if freq == "D" and from_date:
        query = query.filter(FactIndicatorTs.trade_date >= from_date)
    if freq == "D" and to_date:
        query = query.filter(FactIndicatorTs.trade_date <= to_date)
    
    if freq == "W" and from_date:
        query = query.filter(FactIndicatorTs.week_end >= from_date)
    if freq == "W" and to_date:
        query = query.filter(FactIndicatorTs.week_end <= to_date)
    
    # 执行查询
    results = query.order_by(
        FactIndicatorTs.trade_date if freq == "D" else FactIndicatorTs.week_end
    ).all()
    
    # 转换为返回格式
    series = []
    for r in results:
        date_key = r.trade_date if freq == "D" else r.week_end
        series.append({
            "date": date_key.isoformat() if date_key else None,
            "value": float(r.value) if r.value else None
        })
    
    # 获取最新更新时间
    update_time = None
    if results:
        latest = max(results, key=lambda x: x.updated_at if x.updated_at else date.min)
        update_time = latest.updated_at.isoformat() if latest.updated_at else None
    
    return {
        "indicator_code": indicator_code,
        "indicator_name": indicator.indicator_name,
        "unit": indicator.unit,
        "series": series,
        "update_time": update_time
    }


def query_indicator_metrics(
    db: Session,
    indicator_code: str,
    region_code: Optional[str] = None,
    date_key: Optional[date] = None
) -> Dict:
    """
    查询预计算metrics
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        region_code: 区域代码（可选）
        date_key: 日期键
    
    Returns:
        metrics字典
    """
    query = db.query(FactIndicatorMetrics).filter(
        FactIndicatorMetrics.indicator_code == indicator_code
    )
    
    if region_code:
        query = query.filter(FactIndicatorMetrics.region_code == region_code)
    
    if date_key:
        query = query.filter(FactIndicatorMetrics.date_key == date_key)
    
    result = query.first()
    
    if not result:
        return {}
    
    return {
        "value": float(result.value) if result.value else None,
        "chg_1": float(result.chg_1) if result.chg_1 else None,
        "chg_5": float(result.chg_5) if result.chg_5 else None,
        "chg_10": float(result.chg_10) if result.chg_10 else None,
        "chg_30": float(result.chg_30) if result.chg_30 else None,
        "mom": float(result.mom) if result.mom else None,
        "yoy": float(result.yoy) if result.yoy else None
    }
