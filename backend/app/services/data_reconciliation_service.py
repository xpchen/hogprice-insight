"""数据对账服务：缺失日期/重复/异常值检查"""
from typing import Dict, List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models import FactIndicatorTs, DimIndicator


def check_missing_dates(
    db: Session,
    indicator_code: str,
    region_code: Optional[str] = None,
    freq: str = "D",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[date]:
    """
    检查缺失日期
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        region_code: 区域代码（可选）
        freq: 频率（D/W）
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        缺失日期列表
    """
    # 获取指标信息
    indicator = db.query(DimIndicator).filter(
        DimIndicator.indicator_code == indicator_code
    ).first()
    
    if not indicator:
        return []
    
    # 设置默认日期范围
    if not end_date:
        end_date = date.today()
    if not start_date:
        if freq == "D":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(weeks=12)
    
    # 查询已有数据的日期
    query = db.query(FactIndicatorTs).filter(
        FactIndicatorTs.indicator_code == indicator_code,
        FactIndicatorTs.freq == freq
    )
    
    if region_code:
        query = query.filter(FactIndicatorTs.region_code == region_code)
    
    if freq == "D":
        query = query.filter(
            and_(
                FactIndicatorTs.trade_date >= start_date,
                FactIndicatorTs.trade_date <= end_date
            )
        )
        existing_dates = {r.trade_date for r in query.all() if r.trade_date}
        
        # 生成期望的日期列表
        expected_dates = set()
        current_date = start_date
        while current_date <= end_date:
            expected_dates.add(current_date)
            current_date += timedelta(days=1)
    else:
        query = query.filter(
            and_(
                FactIndicatorTs.week_end >= start_date,
                FactIndicatorTs.week_end <= end_date
            )
        )
        existing_dates = {r.week_end for r in query.all() if r.week_end}
        
        # 生成期望的周列表（简化：每周的周日）
        expected_dates = set()
        current_date = start_date
        while current_date <= end_date:
            # 找到该周的周日
            days_until_sunday = (6 - current_date.weekday()) % 7
            if days_until_sunday == 0:
                sunday = current_date
            else:
                sunday = current_date + timedelta(days=days_until_sunday)
            if sunday <= end_date:
                expected_dates.add(sunday)
            current_date += timedelta(weeks=1)
    
    # 找出缺失的日期
    missing_dates = sorted(expected_dates - existing_dates)
    
    return missing_dates


def check_duplicates(
    db: Session,
    indicator_code: str,
    region_code: Optional[str] = None,
    freq: str = "D",
    date_range: Optional[Dict[str, date]] = None
) -> List[Dict]:
    """
    检查重复记录
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        region_code: 区域代码（可选）
        freq: 频率（D/W）
        date_range: 日期范围
    
    Returns:
        重复记录列表
    """
    query = db.query(FactIndicatorTs).filter(
        FactIndicatorTs.indicator_code == indicator_code,
        FactIndicatorTs.freq == freq
    )
    
    if region_code:
        query = query.filter(FactIndicatorTs.region_code == region_code)
    
    if date_range:
        start_date = date_range.get("start")
        end_date = date_range.get("end")
        if freq == "D" and start_date and end_date:
            query = query.filter(
                and_(
                    FactIndicatorTs.trade_date >= start_date,
                    FactIndicatorTs.trade_date <= end_date
                )
            )
        elif freq == "W" and start_date and end_date:
            query = query.filter(
                and_(
                    FactIndicatorTs.week_end >= start_date,
                    FactIndicatorTs.week_end <= end_date
                )
            )
    
    # 查找重复（基于唯一键）
    if freq == "D":
        duplicates_query = db.query(
            FactIndicatorTs.indicator_code,
            FactIndicatorTs.region_code,
            FactIndicatorTs.trade_date,
            func.count().label('count')
        ).filter(
            FactIndicatorTs.indicator_code == indicator_code,
            FactIndicatorTs.freq == freq
        ).group_by(
            FactIndicatorTs.indicator_code,
            FactIndicatorTs.region_code,
            FactIndicatorTs.trade_date
        ).having(func.count() > 1)
    else:
        duplicates_query = db.query(
            FactIndicatorTs.indicator_code,
            FactIndicatorTs.region_code,
            FactIndicatorTs.week_end,
            func.count().label('count')
        ).filter(
            FactIndicatorTs.indicator_code == indicator_code,
            FactIndicatorTs.freq == freq
        ).group_by(
            FactIndicatorTs.indicator_code,
            FactIndicatorTs.region_code,
            FactIndicatorTs.week_end
        ).having(func.count() > 1)
    
    duplicates = []
    for dup in duplicates_query.all():
        duplicates.append({
            "indicator_code": dup.indicator_code,
            "region_code": dup.region_code,
            "date": dup.trade_date if freq == "D" else dup.week_end,
            "count": dup.count
        })
    
    return duplicates


def check_anomalies(
    db: Session,
    indicator_code: str,
    region_code: Optional[str] = None,
    threshold_config: Optional[Dict] = None
) -> List[Dict]:
    """
    检查异常值
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        region_code: 区域代码（可选）
        threshold_config: 阈值配置
            {
                "min": float,  # 最小值
                "max": float,  # 最大值
                "std_multiplier": float  # 标准差倍数（默认3）
            }
    
    Returns:
        异常值列表
    """
    query = db.query(FactIndicatorTs).filter(
        FactIndicatorTs.indicator_code == indicator_code,
        FactIndicatorTs.value.isnot(None)
    )
    
    if region_code:
        query = query.filter(FactIndicatorTs.region_code == region_code)
    
    records = query.all()
    
    if not records:
        return []
    
    values = [float(r.value) for r in records if r.value is not None]
    
    if not values:
        return []
    
    import statistics
    
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0
    
    # 默认阈值配置
    if not threshold_config:
        threshold_config = {
            "std_multiplier": 3
        }
    
    min_threshold = threshold_config.get("min")
    max_threshold = threshold_config.get("max")
    std_multiplier = threshold_config.get("std_multiplier", 3)
    
    # 如果没有明确指定min/max，使用标准差方法
    if min_threshold is None:
        min_threshold = mean - std_multiplier * std
    if max_threshold is None:
        max_threshold = mean + std_multiplier * std
    
    anomalies = []
    for r in records:
        if r.value is None:
            continue
        
        value = float(r.value)
        date_key = r.trade_date if r.freq == "D" else r.week_end
        
        if value < min_threshold or value > max_threshold:
            anomalies.append({
                "indicator_code": r.indicator_code,
                "region_code": r.region_code,
                "date": date_key.isoformat() if date_key else None,
                "value": value,
                "mean": mean,
                "std": std,
                "deviation": abs(value - mean) / std if std > 0 else 0
            })
    
    return anomalies
