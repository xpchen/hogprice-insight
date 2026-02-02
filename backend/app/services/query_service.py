from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case, extract
from sqlalchemy.dialects.mysql import JSON

from app.models import FactObservation, DimMetric, DimGeo, DimCompany, DimWarehouse


def query_timeseries(
    db: Session,
    date_range: Optional[Dict[str, date]] = None,
    metric_ids: Optional[List[int]] = None,
    geo_ids: Optional[List[int]] = None,
    company_ids: Optional[List[int]] = None,
    warehouse_ids: Optional[List[int]] = None,
    tags_filter: Optional[Dict] = None,
    group_by: Optional[List[str]] = None,
    time_dimension: str = "daily"  # daily/weekly/monthly/quarterly/yearly
) -> Dict:
    """
    查询时间序列数据
    
    Args:
        db: 数据库会话
        date_range: {"start": date, "end": date}，可选
        metric_ids: 指标ID列表
        geo_ids: 地区ID列表
        company_ids: 企业ID列表
        warehouse_ids: 交割库ID列表
        tags_filter: tags过滤条件，如 {"pig_type": "商品猪"}
        group_by: 分组字段，如 ["geo", "company"]
        time_dimension: 时间维度，daily/weekly/monthly/yearly
    
    Returns:
        {
            "series": [
                {
                    "name": "系列名称",
                    "data": [[date_str, value], ...]
                }
            ],
            "categories": [date_str, ...]  # 所有日期
        }
"""
    # 构建基础查询
    query = db.query(
        FactObservation.obs_date,
        FactObservation.value,
        FactObservation.metric_id,
        FactObservation.geo_id,
        FactObservation.company_id,
        FactObservation.warehouse_id,
        DimMetric.metric_name,
        DimMetric.metric_group,
        DimGeo.province.label("geo_name"),
        DimCompany.company_name.label("company_name"),
        DimWarehouse.warehouse_name.label("warehouse_name")
    ).join(
        DimMetric, FactObservation.metric_id == DimMetric.id
    ).outerjoin(
        DimGeo, FactObservation.geo_id == DimGeo.id
    ).outerjoin(
        DimCompany, FactObservation.company_id == DimCompany.id
    ).outerjoin(
        DimWarehouse, FactObservation.warehouse_id == DimWarehouse.id
    )
    
    # 日期范围过滤（可选）
    if date_range:
        query = query.filter(
            and_(
                FactObservation.obs_date >= date_range["start"],
                FactObservation.obs_date <= date_range["end"]
            )
        )
    
    # 应用筛选条件
    if metric_ids:
        query = query.filter(FactObservation.metric_id.in_(metric_ids))
    
    if geo_ids:
        query = query.filter(FactObservation.geo_id.in_(geo_ids))
    
    if company_ids:
        query = query.filter(FactObservation.company_id.in_(company_ids))
    
    if warehouse_ids:
        query = query.filter(FactObservation.warehouse_id.in_(warehouse_ids))
    
    # tags过滤（MySQL JSON查询）
    if tags_filter:
        for key, value in tags_filter.items():
            # MySQL JSON路径查询，使用JSON_UNQUOTE去除引号
            query = query.filter(
                func.json_unquote(
                    func.json_extract(FactObservation.tags_json, f'$.{key}')
                ) == value
            )
    
    # 执行查询
    results = query.order_by(FactObservation.obs_date).all()
    
    # 根据时间维度聚合数据
    if time_dimension != "daily":
        results = _aggregate_by_time_dimension(results, time_dimension)
    
    # 处理group_by
    if group_by:
        return _process_grouped_results(results, group_by, time_dimension)
    else:
        return _process_ungrouped_results(results, time_dimension)


def _aggregate_by_time_dimension(results: List, time_dimension: str) -> List:
    """按时间维度聚合数据"""
    from collections import defaultdict
    
    # 按时间维度分组
    grouped = defaultdict(list)
    
    for row in results:
        obs_date = row.obs_date
        
        if time_dimension == "weekly":
            # 按周聚合：使用年份和周数
            year, week, weekday = obs_date.isocalendar()
            time_key = f"{year}-W{week:02d}"
        elif time_dimension == "monthly":
            # 按月聚合
            time_key = obs_date.strftime("%Y-%m")
        elif time_dimension == "quarterly":
            # 按季度聚合
            quarter = (obs_date.month - 1) // 3 + 1
            time_key = f"{obs_date.year}-Q{quarter}"
        elif time_dimension == "yearly":
            # 按年聚合
            time_key = obs_date.strftime("%Y")
        else:
            # daily，不聚合
            time_key = obs_date.strftime("%Y-%m-%d")
        
        # 构建分组键（指标+维度）
        group_key = (
            row.metric_id,
            row.geo_id or 0,
            row.company_id or 0,
            row.warehouse_id or 0,
            row.metric_name,
            row.geo_name or "",
            row.company_name or "",
            row.warehouse_name or ""
        )
        
        grouped[(time_key, group_key)].append(row)
    
    # 聚合：计算平均值
    aggregated_results = []
    for (time_key, group_key), rows in grouped.items():
        values = [float(r.value) for r in rows if r.value is not None]
        if values:
            avg_value = sum(values) / len(values)
            # 使用第一个row作为模板，更新日期和值
            first_row = rows[0]
            # 创建新的日期（使用时间段的开始日期）
            if time_dimension == "weekly":
                # 使用该周的第一天（周一）
                year, week, _ = first_row.obs_date.isocalendar()
                # 计算该周周一的日期
                days_since_monday = first_row.obs_date.weekday()  # 0=Monday, 6=Sunday
                new_date = first_row.obs_date - timedelta(days=days_since_monday)
            elif time_dimension == "monthly":
                new_date = date(first_row.obs_date.year, first_row.obs_date.month, 1)
            elif time_dimension == "quarterly":
                # 使用该季度的第一天
                quarter = (first_row.obs_date.month - 1) // 3 + 1
                quarter_start_month = (quarter - 1) * 3 + 1
                new_date = date(first_row.obs_date.year, quarter_start_month, 1)
            elif time_dimension == "yearly":
                new_date = date(first_row.obs_date.year, 1, 1)
            else:
                new_date = first_row.obs_date
            
            # 创建新的结果对象（使用namedtuple或简单类）
            class AggregatedRow:
                def __init__(self, original_row, new_date, new_value):
                    self.obs_date = new_date
                    self.value = new_value
                    self.metric_id = original_row.metric_id
                    self.geo_id = original_row.geo_id
                    self.company_id = original_row.company_id
                    self.warehouse_id = original_row.warehouse_id
                    self.metric_name = original_row.metric_name
                    self.metric_group = original_row.metric_group
                    self.geo_name = original_row.geo_name
                    self.company_name = original_row.company_name
                    self.warehouse_name = original_row.warehouse_name
            
            aggregated_results.append(AggregatedRow(first_row, new_date, avg_value))
    
    # 按日期排序
    aggregated_results.sort(key=lambda x: x.obs_date)
    return aggregated_results


def _process_ungrouped_results(results: List, time_dimension: str = "daily") -> Dict:
    """处理未分组的结果"""
    # 按指标分组
    series_dict = {}
    all_dates = set()
    
    for row in results:
        if time_dimension == "weekly":
            year, week, _ = row.obs_date.isocalendar()
            date_str = f"{year}-W{week:02d}"
        elif time_dimension == "quarterly":
            quarter = (row.obs_date.month - 1) // 3 + 1
            date_str = f"{row.obs_date.year}-Q{quarter}"
        elif time_dimension == "monthly":
            date_str = row.obs_date.strftime("%Y-%m")
        elif time_dimension == "yearly":
            date_str = row.obs_date.strftime("%Y")
        else:
            date_str = row.obs_date.strftime("%Y-%m-%d")
        
        all_dates.add(date_str)
        
        # 构建系列名称
        name_parts = [row.metric_name]
        if row.geo_name:
            name_parts.append(row.geo_name)
        if row.company_name:
            name_parts.append(row.company_name)
        if row.warehouse_name:
            name_parts.append(row.warehouse_name)
        
        series_name = " - ".join(name_parts)
        
        if series_name not in series_dict:
            series_dict[series_name] = {}
        
        if row.value is not None:
            series_dict[series_name][date_str] = float(row.value)
    
    # 转换为ECharts格式
    categories = sorted(all_dates)
    series = []
    
    for series_name, data_dict in series_dict.items():
        data = [[date_str, data_dict.get(date_str)] for date_str in categories]
        series.append({
            "name": series_name,
            "data": data
        })
    
    return {
        "series": series,
        "categories": categories
    }


def _process_grouped_results(results: List, group_by: List[str], time_dimension: str = "daily") -> Dict:
    """处理分组结果"""
    # 构建分组键
    grouped_data = {}
    all_dates = set()
    
    for row in results:
        if time_dimension == "weekly":
            year, week, _ = row.obs_date.isocalendar()
            date_str = f"{year}-W{week:02d}"
        elif time_dimension == "quarterly":
            quarter = (row.obs_date.month - 1) // 3 + 1
            date_str = f"{row.obs_date.year}-Q{quarter}"
        elif time_dimension == "monthly":
            date_str = row.obs_date.strftime("%Y-%m")
        elif time_dimension == "yearly":
            date_str = row.obs_date.strftime("%Y")
        else:
            date_str = row.obs_date.strftime("%Y-%m-%d")
        
        all_dates.add(date_str)
        
        # 构建分组键
        group_key_parts = []
        for gb in group_by:
            if gb == "geo" and row.geo_name:
                group_key_parts.append(row.geo_name)
            elif gb == "company" and row.company_name:
                group_key_parts.append(row.company_name)
            elif gb == "warehouse" and row.warehouse_name:
                group_key_parts.append(row.warehouse_name)
            elif gb == "metric" and row.metric_name:
                group_key_parts.append(row.metric_name)
        
        group_key = " - ".join(group_key_parts) if group_key_parts else "其他"
        
        if group_key not in grouped_data:
            grouped_data[group_key] = {}
        
        # 累加或平均（这里简单累加，实际可能需要根据业务需求调整）
        if date_str not in grouped_data[group_key]:
            grouped_data[group_key][date_str] = []
        
        if row.value is not None:
            grouped_data[group_key][date_str].append(float(row.value))
    
    # 计算平均值
    categories = sorted(all_dates)
    series = []
    
    for group_key, date_values in grouped_data.items():
        data = []
        for date_str in categories:
            values = date_values.get(date_str, [])
            avg_value = sum(values) / len(values) if values else None
            data.append([date_str, avg_value])
        
        series.append({
            "name": group_key,
            "data": data
        })
    
    return {
        "series": series,
        "categories": categories
    }


def query_topn(
    db: Session,
    metric_id: int,
    target_date: date,
    group_by: str,
    n: int = 10,
    sort_by: str = "last"  # last/avg/change
) -> List[Dict]:
    """
    查询TopN数据
    
    Args:
        db: 数据库会话
        metric_id: 指标ID
        target_date: 目标日期
        group_by: 分组字段（geo/company/warehouse）
        n: 返回数量
        sort_by: 排序方式（last/avg/change）
    
    Returns:
        [
            {
                "name": "名称",
                "value": float,
                "change": float  # 变化率（如果sort_by=change）
            }
        ]
    """
    # TODO: 实现TopN查询
    return []
