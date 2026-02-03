"""指标预计算服务（同比/环比/5日10日变化）"""
from typing import Dict, List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models import FactIndicatorTs, FactIndicatorMetrics, DimIndicator


def calculate_metrics(
    db: Session,
    indicator_code: str,
    region_code: Optional[str] = None,
    freq: str = "D"
) -> None:
    """
    计算指标的预计算metrics并写入fact_indicator_metrics
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        region_code: 区域代码（如果为None，则计算所有区域）
        freq: 频率（D/W）
    """
    # 构建查询条件
    query = db.query(FactIndicatorTs).filter(
        FactIndicatorTs.indicator_code == indicator_code,
        FactIndicatorTs.freq == freq,
        FactIndicatorTs.value.isnot(None)
    )
    
    if region_code:
        query = query.filter(FactIndicatorTs.region_code == region_code)
    
    # 按日期排序
    if freq == "D":
        query = query.order_by(FactIndicatorTs.trade_date)
        date_field = FactIndicatorTs.trade_date
    else:
        query = query.order_by(FactIndicatorTs.week_end)
        date_field = FactIndicatorTs.week_end
    
    records = query.all()
    
    if not records:
        return
    
    # 按日期键分组
    records_dict = {}
    for r in records:
        date_key = r.trade_date if freq == "D" else r.week_end
        records_dict[date_key] = r
    
    # 计算每个日期的metrics
    metrics_to_insert = []
    metrics_to_update = []
    
    for date_key in sorted(records_dict.keys()):
        current_record = records_dict[date_key]
        current_value = float(current_record.value) if current_record.value else None
        
        if current_value is None:
            continue
        
        # 计算变化量
        chg_1 = None
        chg_5 = None
        chg_10 = None
        chg_30 = None
        
        if freq == "D":
            # 日频：计算1日、5日、10日、30日变化
            date_1 = date_key - timedelta(days=1)
            date_5 = date_key - timedelta(days=5)
            date_10 = date_key - timedelta(days=10)
            date_30 = date_key - timedelta(days=30)
        else:
            # 周频：计算1周、5周、10周、30周变化
            date_1 = date_key - timedelta(weeks=1)
            date_5 = date_key - timedelta(weeks=5)
            date_10 = date_key - timedelta(weeks=10)
            date_30 = date_key - timedelta(weeks=30)
        
        if date_1 in records_dict:
            prev_value = float(records_dict[date_1].value) if records_dict[date_1].value else None
            if prev_value is not None:
                chg_1 = current_value - prev_value
        
        if date_5 in records_dict:
            prev_value = float(records_dict[date_5].value) if records_dict[date_5].value else None
            if prev_value is not None:
                chg_5 = current_value - prev_value
        
        if date_10 in records_dict:
            prev_value = float(records_dict[date_10].value) if records_dict[date_10].value else None
            if prev_value is not None:
                chg_10 = current_value - prev_value
        
        if date_30 in records_dict:
            prev_value = float(records_dict[date_30].value) if records_dict[date_30].value else None
            if prev_value is not None:
                chg_30 = current_value - prev_value
        
        # 计算同比（Year-over-Year）
        yoy = None
        if freq == "D":
            year_ago_date = date(date_key.year - 1, date_key.month, date_key.day)
        else:
            # 周频：查找去年同周
            year_ago_date = date(date_key.year - 1, date_key.month, date_key.day)
            # 简化处理：查找最接近的日期
            for d in sorted(records_dict.keys(), reverse=True):
                if d.year == year_ago_date.year and abs((d - year_ago_date).days) < 7:
                    year_ago_date = d
                    break
        
        if year_ago_date in records_dict:
            year_ago_value = float(records_dict[year_ago_date].value) if records_dict[year_ago_date].value else None
            if year_ago_value is not None and year_ago_value != 0:
                yoy = ((current_value - year_ago_value) / year_ago_value) * 100
        
        # 计算环比（Month-over-Month）
        mom = None
        if freq == "D":
            # 查找上个月同一天
            if date_key.month == 1:
                month_ago_date = date(date_key.year - 1, 12, date_key.day)
            else:
                month_ago_date = date(date_key.year, date_key.month - 1, date_key.day)
        else:
            # 周频：查找4周前
            month_ago_date = date_key - timedelta(weeks=4)
        
        # 查找最接近的日期
        closest_date = None
        min_diff = float('inf')
        for d in records_dict.keys():
            diff = abs((d - month_ago_date).days)
            if diff < min_diff:
                min_diff = diff
                closest_date = d
        
        if closest_date and min_diff < 7:  # 允许7天误差
            month_ago_value = float(records_dict[closest_date].value) if records_dict[closest_date].value else None
            if month_ago_value is not None and month_ago_value != 0:
                mom = ((current_value - month_ago_value) / month_ago_value) * 100
        
        # 检查是否已存在metrics记录
        existing_metrics = db.query(FactIndicatorMetrics).filter(
            FactIndicatorMetrics.indicator_code == indicator_code,
            FactIndicatorMetrics.region_code == current_record.region_code,
            FactIndicatorMetrics.freq == freq,
            FactIndicatorMetrics.date_key == date_key
        ).first()
        
        metrics_data = {
            "indicator_code": indicator_code,
            "region_code": current_record.region_code,
            "freq": freq,
            "date_key": date_key,
            "value": current_value,
            "chg_1": chg_1,
            "chg_5": chg_5,
            "chg_10": chg_10,
            "chg_30": chg_30,
            "mom": mom,
            "yoy": yoy
        }
        
        if existing_metrics:
            # 更新现有记录
            for key, value in metrics_data.items():
                setattr(existing_metrics, key, value)
            metrics_to_update.append(existing_metrics)
        else:
            # 插入新记录
            metrics_to_insert.append(FactIndicatorMetrics(**metrics_data))
    
    # 批量插入和更新
    if metrics_to_insert:
        db.bulk_save_objects(metrics_to_insert)
    
    db.commit()


def calculate_all_indicators_metrics(db: Session, freq: Optional[str] = None) -> None:
    """
    计算所有指标的metrics
    
    Args:
        db: 数据库会话
        freq: 频率（D/W），如果为None则计算所有频率
    """
    # 获取所有指标
    query = db.query(DimIndicator)
    if freq:
        query = query.filter(DimIndicator.freq == freq)
    
    indicators = query.all()
    
    for indicator in indicators:
        # 获取该指标的所有区域
        regions_query = db.query(FactIndicatorTs.region_code).filter(
            FactIndicatorTs.indicator_code == indicator.indicator_code,
            FactIndicatorTs.freq == indicator.freq
        ).distinct()
        
        regions = [r[0] for r in regions_query.all()]
        
        for region_code in regions:
            try:
                calculate_metrics(db, indicator.indicator_code, region_code, indicator.freq)
            except Exception as e:
                # 记录错误但继续处理其他指标
                print(f"计算指标 {indicator.indicator_code} 区域 {region_code} 的metrics失败: {str(e)}")
                continue
