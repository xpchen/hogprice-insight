from typing import Dict, List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from collections import defaultdict

from app.models import FactObservation, DimMetric, DimGeo, DimCompany, DimWarehouse


def query_seasonality(
    db: Session,
    metric_id: int,
    years: List[int],
    filters: Optional[Dict] = None,
    x_mode: str = "week_of_year",  # week_of_year | month_day
    agg: str = "mean"  # mean | last
) -> Dict:
    """
    查询季节性数据（多年叠线）
    
    Args:
        db: 数据库会话
        metric_id: 指标ID（单指标）
        years: 年份列表，如 [2021, 2022, 2023, 2024, 2025, 2026]
        filters: 过滤条件，包含 geo_ids, company_ids, warehouse_ids, tags_filter
        x_mode: x轴模式，week_of_year（周序号）或 month_day（月-日）
        agg: 聚合方式，mean（平均值）或 last（最后值）
    
    Returns:
        {
            "x_values": [1, 2, ..., 52] 或 ["01-01", "01-02", ...],
            "series": [
                {"year": 2021, "values": [null, 12.5, ...]},
                {"year": 2022, "values": [11.8, 12.3, ...]}
            ],
            "meta": {
                "unit": "元/千克",
                "freq": "daily",
                "metric_name": "标肥价差"
            }
        }
    """
    if not years:
        return {
            "x_values": [],
            "series": [],
            "meta": {}
        }
    
    # 构建日期范围（覆盖所有年份）
    min_year = min(years)
    max_year = max(years)
    date_start = date(min_year, 1, 1)
    date_end = date(max_year, 12, 31)
    
    # 构建基础查询
    query = db.query(
        FactObservation.obs_date,
        FactObservation.value,
        DimMetric.metric_name,
        DimMetric.unit,
        DimMetric.freq
    ).join(
        DimMetric, FactObservation.metric_id == DimMetric.id
    ).filter(
        FactObservation.metric_id == metric_id,
        FactObservation.obs_date >= date_start,
        FactObservation.obs_date <= date_end
    )
    
    # 应用过滤条件
    filters = filters or {}
    if filters.get("geo_ids"):
        query = query.filter(FactObservation.geo_id.in_(filters["geo_ids"]))
    
    if filters.get("company_ids"):
        query = query.filter(FactObservation.company_id.in_(filters["company_ids"]))
    
    if filters.get("warehouse_ids"):
        query = query.filter(FactObservation.warehouse_id.in_(filters["warehouse_ids"]))
    
    # tags过滤
    if filters.get("tags_filter"):
        from sqlalchemy.dialects.mysql import JSON
        for key, value in filters["tags_filter"].items():
            query = query.filter(
                func.json_unquote(
                    func.json_extract(FactObservation.tags_json, f'$.{key}')
                ) == value
            )
    
    # 执行查询
    results = query.order_by(FactObservation.obs_date).all()
    
    if not results:
        return {
            "x_values": [],
            "series": [],
            "meta": {
                "unit": "",
                "freq": "daily",
                "metric_name": ""
            }
        }
    
    # 获取元数据（从第一条记录）
    first_result = results[0]
    meta = {
        "unit": first_result.unit or "",
        "freq": first_result.freq or "daily",
        "metric_name": first_result.metric_name or ""
    }
    
    # 按年份和x值分组
    if x_mode == "week_of_year":
        result = _process_week_of_year(results, years, agg)
        result["meta"] = meta
        return result
    else:  # month_day
        return _process_month_day(results, years, agg, meta)


def _process_week_of_year(results: List, years: List[int], agg: str) -> Dict:
    """处理week_of_year模式（x = 1..52）"""
    # 按年份和周序号分组
    grouped = defaultdict(lambda: defaultdict(list))  # {year: {week: [values]}}
    
    for row in results:
        obs_date = row.obs_date
        year = obs_date.year
        
        if year not in years:
            continue
        
        # 计算周序号（ISO周）
        year_iso, week_iso, weekday_iso = obs_date.isocalendar()
        
        # 如果跨年（ISO周可能属于下一年），使用原年份
        if year_iso != year:
            # 使用原年份的第一周或最后一周
            if obs_date.month == 12:
                # 12月的数据，如果ISO周属于下一年，归入当前年的最后一周
                week_iso = 52
            else:
                week_iso = 1
        
        # 限制在1-52范围内
        week_iso = max(1, min(52, week_iso))
        
        if row.value is not None:
            grouped[year][week_iso].append(float(row.value))
    
    # 生成x轴值（1-52）
    x_values = list(range(1, 53))
    
    # 生成系列数据
    series = []
    for year in sorted(years):
        values = []
        for week in x_values:
            week_values = grouped[year].get(week, [])
            if week_values:
                if agg == "mean":
                    values.append(sum(week_values) / len(week_values))
                else:  # last
                    values.append(week_values[-1])
            else:
                values.append(None)  # 缺失值
        
        series.append({
            "year": year,
            "values": values
        })
    
    return {
        "x_values": x_values,
        "series": series,
        "meta": {}  # meta会在外层添加
    }


def _process_month_day(results: List, years: List[int], agg: str, meta: Dict) -> Dict:
    """处理month_day模式（x = "01-01".."12-31"）"""
    # 按年份和月-日分组
    grouped = defaultdict(lambda: defaultdict(list))  # {year: {"MM-DD": [values]}}
    
    for row in results:
        obs_date = row.obs_date
        year = obs_date.year
        
        if year not in years:
            continue
        
        # 处理闰年2-29：丢弃或合并到2-28
        if obs_date.month == 2 and obs_date.day == 29:
            # 丢弃2-29的数据（MVP策略）
            continue
        
        month_day = obs_date.strftime("%m-%d")
        
        if row.value is not None:
            grouped[year][month_day].append(float(row.value))
    
    # 生成x轴值（01-01到12-31，排除2-29）
    x_values = []
    for month in range(1, 13):
        days_in_month = 31
        if month == 2:
            days_in_month = 28  # 排除2-29
        elif month in [4, 6, 9, 11]:
            days_in_month = 30
        
        for day in range(1, days_in_month + 1):
            x_values.append(f"{month:02d}-{day:02d}")
    
    # 生成系列数据
    series = []
    for year in sorted(years):
        values = []
        for month_day in x_values:
            day_values = grouped[year].get(month_day, [])
            if day_values:
                if agg == "mean":
                    values.append(sum(day_values) / len(day_values))
                else:  # last
                    values.append(day_values[-1])
            else:
                values.append(None)  # 缺失值
        
        series.append({
            "year": year,
            "values": values
        })
    
    return {
        "x_values": x_values,
        "series": series,
        "meta": meta
    }
