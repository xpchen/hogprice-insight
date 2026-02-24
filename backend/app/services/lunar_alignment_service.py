"""农历对齐服务"""
from typing import Dict, Optional, List, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import FactIndicatorTs

# 尝试导入lunar-python库，如果没有则使用简化实现
try:
    from lunar_python import Lunar, Solar
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
        try:
            # 注意：Lunar.fromYmd() 的参数是农历日期，不是公历日期！
            # 我们需要先创建公历日期（Solar），然后转换为农历（Lunar）
            solar = Solar.fromYmd(solar_date.year, solar_date.month, solar_date.day)
            lunar = solar.getLunar()
            lunar_year = lunar.getYear()
            lunar_month = lunar.getMonth()
            lunar_day = lunar.getDay()
            
            
            # 检查是否为闰月：通过月份中文名称判断
            is_leap_month = False
            try:
                # 方法：通过月份中文名称判断（如果包含"闰"字则为闰月）
                month_str = str(lunar.getMonthInChinese())
                is_leap_month = '闰' in month_str
            except Exception as e:
                # 如果无法获取中文月份，尝试其他方法
                try:
                    # 尝试通过创建该月第一天来判断
                    lunar_first = Lunar.fromYmd(lunar_year, lunar_month, 1)
                    month_str = str(lunar_first.getMonthInChinese())
                    is_leap_month = '闰' in month_str
                except:
                    is_leap_month = False
            
            # 计算lunar_day_index（以正月初八为起点）
            lunar_day_index = _calculate_lunar_day_index(lunar_year, lunar_month, lunar_day, is_leap_month)
            
            result = {
                "lunar_year": lunar_year,
                "lunar_month": lunar_month,
                "lunar_day": lunar_day,
                "is_leap_month": is_leap_month,
                "lunar_day_index": lunar_day_index
            }
            
            
            return result
        except Exception:
            # 降级处理
            return {
                "lunar_year": solar_date.year,
                "lunar_month": solar_date.month,
                "lunar_day": solar_date.day,
                "is_leap_month": False,
                "lunar_day_index": None
            }
    else:
        # 简化实现：返回基本结构，实际计算需要安装lunar-python
        return {
            "lunar_year": solar_date.year,
            "lunar_month": solar_date.month,
            "lunar_day": solar_date.day,
            "is_leap_month": False,
            "lunar_day_index": None  # 需要lunar-python库才能计算
        }


def _calculate_lunar_day_index(lunar_year: int, lunar_month: int, lunar_day: int, is_leap_month: bool) -> Optional[int]:
    """
    计算农历日期索引（以正月初八为起点，index=1，到腊月二十八结束）
    
    对齐规则：
    - 正月初八 = index 1
    - 正月初九 = index 2
    - ...
    - 腊月二十八 = 最后一个有效索引
    - 闰月：返回None，需要单独处理
    
    Returns:
        int: 农历日期索引（1开始），如果是闰月或不在范围内则返回None
    """
    if HAS_LUNAR_LIB:
        try:
            from lunar_python import Solar
            # 获取正月初一的日期（先创建农历日期，再转换为公历）
            lunar_new_year = Lunar.fromYmd(lunar_year, 1, 1)
            # 如果当前日期是闰月，需要特殊处理
            # 先尝试创建正常月份，如果失败再尝试闰月
            try:
                current_lunar = Lunar.fromYmd(lunar_year, lunar_month, lunar_day)
            except:
                # 如果是闰月，可能需要使用不同的方法
                # 暂时使用正常月份
                current_lunar = Lunar.fromYmd(lunar_year, lunar_month, lunar_day)
            
            # 闰月单独处理，返回None
            if is_leap_month:
                return None
            
            # 计算从正月初一到当前日期的天数
            solar_new_year = lunar_new_year.getSolar()
            solar_current = current_lunar.getSolar()
            
            # 获取公历日期对象（toYmd()返回字符串，需要转换为date对象）
            # lunar-python的getSolar()返回Solar对象，需要获取年月日
            from datetime import date as date_class
            new_year_date = date_class(solar_new_year.getYear(), solar_new_year.getMonth(), solar_new_year.getDay())
            current_date = date_class(solar_current.getYear(), solar_current.getMonth(), solar_current.getDay())
            
            # 计算天数差
            days_diff = (current_date - new_year_date).days
            
            # 正月初八是第8天，所以index = days_diff - 7
            lunar_day_index = days_diff - 7
            
            # 调试：打印计算过程
            # 注意：这里的lunar_year/lunar_month/lunar_day是传入的参数（应该已经是正确的农历日期）
            # current_date是转换后的公历日期（用于计算天数差）
            # 如果看到"农历=2025年11月14日, 公历=2026-01-02"这样的错误，说明传入的参数本身就是错的
            # 应该在调用此函数之前（solar_to_lunar函数中）验证转换结果
            
            # 检查是否在有效范围内（正月初八到腊月二十八）
            # 获取腊月二十八的日期（农历日期转换为公历）
            try:
                lunar_dec_28 = Lunar.fromYmd(lunar_year, 12, 28)
                solar_dec_28 = lunar_dec_28.getSolar()
                
                # 获取腊月二十八的公历日期
                solar_dec_28_date = date_class(solar_dec_28.getYear(), solar_dec_28.getMonth(), solar_dec_28.getDay())
                days_to_dec_28 = (solar_dec_28_date - new_year_date).days - 7
                
                # 如果当前日期在正月初八之前，返回None
                if lunar_day_index < 1:
                    return None
                
                # 放宽限制：允许超出腊月二十八的数据（最多到400天）
                # 这样可以包含跨年的数据（如2026年2月的数据可能属于2025年农历年）
                if lunar_day_index > days_to_dec_28:
                    # 如果超出太多（>400天），返回None；否则允许
                    if lunar_day_index > 400:
                        return None
            except Exception as e:
                # 如果无法获取腊月二十八，使用简化判断
                if lunar_day_index < 1:
                    return None
                # 允许最大400天的范围
                if lunar_day_index > 400:
                    return None
            
            return lunar_day_index
        except Exception as e:
            # 如果计算失败，返回None
            return None
    else:
        # 简化实现：如果没有lunar-python库，返回None
        return None


def get_leap_month_info(lunar_year: int) -> Optional[Dict]:
    """
    获取指定农历年份的闰月信息
    
    Returns:
        {
            "leap_month": int,  # 闰月月份（如6表示闰六月）
            "leap_month_start": date,  # 闰月开始日期（公历）
            "leap_month_end": date  # 闰月结束日期（公历）
        } 或 None（如果没有闰月）
    """
    if not HAS_LUNAR_LIB:
        return None
    
    try:
        # 检查是否有闰月
        # 遍历12个月，查找闰月
        for month in range(1, 13):
            try:
                # 尝试创建该月的日期
                lunar_test = Lunar.fromYmd(lunar_year, month, 1)
                
                # 检查是否为闰月：通过月份中文名称判断
                is_leap = False
                try:
                    month_str = str(lunar_test.getMonthInChinese())
                    is_leap = '闰' in month_str
                except:
                    pass
                
                if is_leap:
                    # 找到闰月，返回公历 date 范围
                    solar = lunar_test.getSolar()
                    leap_start = date(solar.getYear(), solar.getMonth(), solar.getDay())
                    try:
                        leap_days = lunar_test.getDayCount()
                        leap_end_date = leap_start + timedelta(days=leap_days - 1)
                    except Exception:
                        leap_end_date = leap_start + timedelta(days=29)
                    return {
                        "leap_month": month,
                        "leap_month_start": leap_start,
                        "leap_month_end": leap_end_date
                    }
            except Exception as e:
                print(f"检查月份 {month} 失败: {e}")
                continue
        
        return None
    except Exception as e:
        print(f"获取闰月信息失败: {e}")
        return None


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


def get_lunar_year_date_range(lunar_year: int) -> Optional[Tuple[date, date]]:
    """
    获取农历年度的日期范围（2月20日至次年2月10日）
    
    条件：
    - 2月20日必须对应农历的正月
    - 2月10日（次年）必须对应农历的腊月或之前
    
    Args:
        lunar_year: 农历年份（如2024）
    
    Returns:
        (start_date, end_date) 或 None（如果不符合条件）
    """
    if not HAS_LUNAR_LIB:
        return None
    
    try:
        # 获取农历年对应的公历年份范围
        # 农历年通常跨越两个公历年份
        # 例如：2024年农历年从2024年2月10日（正月初一）到2025年1月28日（腊月二十九）
        
        # 获取正月初一的公历日期
        lunar_new_year = Lunar.fromYmd(lunar_year, 1, 1)
        solar_new_year = lunar_new_year.getSolar().toYmd()
        
        # 计算2月20日（正月初一所在公历年份）
        solar_year = solar_new_year.year
        feb_20 = date(solar_year, 2, 20)
        
        # 计算次年2月10日
        next_year_feb_10 = date(solar_year + 1, 2, 10)
        
        # 检查条件：
        # 1. 2月20日必须对应农历的正月
        feb_20_lunar = Lunar.fromYmd(solar_year, 2, 20)
        if feb_20_lunar.getMonth() != 1:
            return None
        
        # 2. 次年2月10日必须对应农历的腊月或之前
        next_feb_10_lunar = Lunar.fromYmd(solar_year + 1, 2, 10)
        if next_feb_10_lunar.getMonth() > 12:
            return None
        
        return (feb_20, next_year_feb_10)
    except Exception as e:
        print(f"获取农历年度日期范围失败: {e}")
        return None


def get_lunar_year_date_range_la_ba(lunar_year: int) -> Optional[Tuple[date, date]]:
    """
    获取农历年度的阳历日期范围：正月初八（含）至腊月二十八（含）。
    用于「屠宰&价格 相关走势」等按年筛选、用阳历日期展示的图表。

    Args:
        lunar_year: 农历年份（如 2024）

    Returns:
        (start_date, end_date) 阳历日期，或 None
    """
    if not HAS_LUNAR_LIB:
        return None
    try:
        from datetime import date as date_class
        # 正月初八
        lunar_jan_8 = Lunar.fromYmd(lunar_year, 1, 8)
        solar_jan_8 = lunar_jan_8.getSolar()
        start_date = date_class(
            solar_jan_8.getYear(),
            solar_jan_8.getMonth(),
            solar_jan_8.getDay(),
        )
        # 腊月二十八
        lunar_dec_28 = Lunar.fromYmd(lunar_year, 12, 28)
        solar_dec_28 = lunar_dec_28.getSolar()
        end_date = date_class(
            solar_dec_28.getYear(),
            solar_dec_28.getMonth(),
            solar_dec_28.getDay(),
        )
        if start_date > end_date:
            return None
        return (start_date, end_date)
    except Exception as e:
        print(f"get_lunar_year_date_range_la_ba 失败 lunar_year={lunar_year}: {e}")
        return None
