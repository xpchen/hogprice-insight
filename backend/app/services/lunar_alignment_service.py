"""农历对齐服务"""
from typing import Dict, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import FactIndicatorTs

# 尝试导入lunar-python库，如果没有则使用简化实现
try:
    from lunar_python import Lunar
    HAS_LUNAR_LIB = True
except ImportError:
    HAS_LUNAR_LIB = False
    print("警告: 未安装lunar-python库，农历对齐功能将使用简化实现。建议安装: pip install lunar-python")


def solar_to_lunar(solar_date: date) -> Dict:
    """
    将公历日期转换为农历日期
    
    Args:
        solar_date: 公历日期
    
    Returns:
        {
            "lunar_year": int,
            "lunar_month": int,
            "lunar_day": int,
            "is_leap_month": bool,
            "lunar_day_index": int  # 以正月初八为起点，index=1
        }
    """
    if HAS_LUNAR_LIB:
        # 使用lunar-python库
        lunar = Lunar.fromYmd(solar_date.year, solar_date.month, solar_date.day)
        lunar_year = lunar.getYear()
        lunar_month = lunar.getMonth()
        lunar_day = lunar.getDay()
        is_leap_month = lunar.isLeapMonth()
        
        # 计算lunar_day_index（以正月初八为起点）
        lunar_day_index = _calculate_lunar_day_index(lunar_year, lunar_month, lunar_day, is_leap_month)
        
        return {
            "lunar_year": lunar_year,
            "lunar_month": lunar_month,
            "lunar_day": lunar_day,
            "is_leap_month": is_leap_month,
            "lunar_day_index": lunar_day_index
        }
    else:
        # 简化实现：返回基本结构，实际计算需要安装lunar-python
        return {
            "lunar_year": solar_date.year,
            "lunar_month": solar_date.month,
            "lunar_day": solar_date.day,
            "is_leap_month": False,
            "lunar_day_index": solar_date.timetuple().tm_yday  # 使用公历天数作为临时替代
        }


def _calculate_lunar_day_index(lunar_year: int, lunar_month: int, lunar_day: int, is_leap_month: bool) -> int:
    """
    计算农历日期索引（以正月初八为起点，index=1）
    
    对齐规则：
    - 正月初八 = index 1
    - 正月初九 = index 2
    - ...
    - 闰月单独计算（从1开始）
    """
    if HAS_LUNAR_LIB:
        # 计算从正月初一到当前日期的天数
        # 正月初八是第8天，所以index = 天数 - 7
        try:
            # 获取正月初一的日期
            lunar_new_year = Lunar.fromYmd(lunar_year, 1, 1)
            current_lunar = Lunar.fromYmd(lunar_year, lunar_month, lunar_day)
            
            if is_leap_month:
                # 闰月：单独计算，从1开始
                # 简化处理：使用月份*30+日期作为索引
                return lunar_month * 30 + lunar_day
            
            # 计算从正月初一到当前日期的天数
            days_diff = (current_lunar.getSolar().toYmd() - lunar_new_year.getSolar().toYmd()).days
            
            # 正月初八是第8天，所以index = days_diff - 7
            lunar_day_index = days_diff - 7
            
            # 确保index >= 1
            if lunar_day_index < 1:
                lunar_day_index = 1
            
            return lunar_day_index
        except:
            # 如果计算失败，使用简化方法
            return lunar_month * 30 + lunar_day
    else:
        # 简化实现
        return lunar_month * 30 + lunar_day


def add_lunar_fields(
    db: Session,
    indicator_code: str,
    region_code: Optional[str] = None
) -> None:
    """
    为日度数据添加农历字段
    
    注意：由于fact_indicator_ts表没有农历字段，这个函数主要用于计算和展示
    实际使用时，可以在查询时动态计算农历字段，或者创建扩展表存储
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        region_code: 区域代码（如果为None，则处理所有区域）
    """
    # 查询日度数据
    query = db.query(FactIndicatorTs).filter(
        FactIndicatorTs.indicator_code == indicator_code,
        FactIndicatorTs.freq == "D",
        FactIndicatorTs.trade_date.isnot(None)
    )
    
    if region_code:
        query = query.filter(FactIndicatorTs.region_code == region_code)
    
    records = query.order_by(FactIndicatorTs.trade_date).all()
    
    # 为每条记录计算农历字段
    # 注意：由于表结构限制，这里只是示例
    # 实际使用时，可以：
    # 1. 在查询时动态计算
    # 2. 创建扩展表存储农历字段
    # 3. 在fact_indicator_ts表中添加lunar_year, lunar_month等字段
    
    lunar_data = []
    for record in records:
        if record.trade_date:
            lunar_info = solar_to_lunar(record.trade_date)
            lunar_data.append({
                "trade_date": record.trade_date,
                "lunar_info": lunar_info
            })
    
    # 返回结果（实际使用时可以存储到扩展表或返回给调用者）
    return lunar_data


def get_seasonality_data_with_lunar(
    db: Session,
    indicator_code: str,
    years: list,
    region_code: Optional[str] = None
) -> Dict:
    """
    获取季节性数据（支持农历对齐）
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        years: 年份列表
        region_code: 区域代码
    
    Returns:
        {
            "years": {
                year: {
                    "lunar_day_index": [index列表],
                    "values": [值列表],
                    "is_leap_month": [是否闰月列表]
                }
            }
        }
    """
    query = db.query(FactIndicatorTs).filter(
        FactIndicatorTs.indicator_code == indicator_code,
        FactIndicatorTs.freq == "D",
        FactIndicatorTs.trade_date.isnot(None)
    )
    
    if region_code:
        query = query.filter(FactIndicatorTs.region_code == region_code)
    
    records = query.order_by(FactIndicatorTs.trade_date).all()
    
    # 按年份分组
    result = {}
    for year in years:
        result[year] = {
            "lunar_day_index": [],
            "values": [],
            "is_leap_month": [],
            "dates": []
        }
    
    for record in records:
        if not record.trade_date:
            continue
        
        year = record.trade_date.year
        if year not in years:
            continue
        
        # 计算农历信息
        lunar_info = solar_to_lunar(record.trade_date)
        
        result[year]["lunar_day_index"].append(lunar_info["lunar_day_index"])
        result[year]["values"].append(float(record.value) if record.value else None)
        result[year]["is_leap_month"].append(lunar_info["is_leap_month"])
        result[year]["dates"].append(record.trade_date.isoformat())
    
    return result
