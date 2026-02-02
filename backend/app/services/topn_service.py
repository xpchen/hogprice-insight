from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, desc
from sqlalchemy.dialects.mysql import JSON

from app.models import FactObservation, DimMetric, DimGeo, DimCompany, DimWarehouse


def query_topn(
    db: Session,
    metric_id: int,
    dimension: str,  # geo | company | warehouse
    window_days: int = 7,
    rank_by: str = "delta",  # delta | pct_change | seasonal_percentile | streak
    filters: Optional[Dict] = None,
    topk: int = 10
) -> Dict:
    """
    查询TopN排名
    
    Args:
        db: 数据库会话
        metric_id: 指标ID
        dimension: 维度（geo/company/warehouse）
        window_days: 窗口天数
        rank_by: 排序方式
        filters: 额外过滤条件
        topk: 返回Top K条
    
    Returns:
        {
            "metric_id": 101,
            "metric_name": "全国标猪价格",
            "dimension": "geo",
            "rank_by": "delta",
            "window_days": 7,
            "items": [
                {
                    "dimension_id": 1,
                    "dimension_name": "北京",
                    "latest_value": 15.5,
                    "baseline_value": 15.0,
                    "delta": 0.5,
                    "pct_change": 0.033,
                    "rank": 1
                }
            ]
        }
    """
    # 确定基准日期和窗口起始日期
    latest_date_result = db.query(func.max(FactObservation.obs_date)).filter(
        FactObservation.metric_id == metric_id
    ).scalar()
    
    if not latest_date_result:
        return {
            "metric_id": metric_id,
            "metric_name": "",
            "dimension": dimension,
            "rank_by": rank_by,
            "window_days": window_days,
            "items": []
        }
    
    latest_date = latest_date_result
    baseline_date = latest_date - timedelta(days=window_days)
    
    # 获取指标名称
    metric = db.query(DimMetric).filter(DimMetric.id == metric_id).first()
    metric_name = metric.metric_name if metric else ""
    
    # 构建基础查询：获取最新值和基准值
    if dimension == "geo":
        dim_table = DimGeo
        dim_id_col = FactObservation.geo_id
        dim_name_col = DimGeo.province
        join_condition = FactObservation.geo_id == DimGeo.id
    elif dimension == "company":
        dim_table = DimCompany
        dim_id_col = FactObservation.company_id
        dim_name_col = DimCompany.company_name
        join_condition = FactObservation.company_id == DimCompany.id
    elif dimension == "warehouse":
        dim_table = DimWarehouse
        dim_id_col = FactObservation.warehouse_id
        dim_name_col = DimWarehouse.warehouse_name
        join_condition = FactObservation.warehouse_id == DimWarehouse.id
    else:
        raise ValueError(f"Unsupported dimension: {dimension}")
    
    # 查询最新值
    latest_subq = db.query(
        dim_id_col.label('dim_id'),
        FactObservation.value.label('latest_value'),
        FactObservation.obs_date.label('obs_date')
    ).filter(
        FactObservation.metric_id == metric_id,
        FactObservation.obs_date == latest_date
    ).subquery()
    
    # 查询基准值（窗口起始日期的值）
    baseline_subq = db.query(
        dim_id_col.label('dim_id'),
        FactObservation.value.label('baseline_value')
    ).filter(
        FactObservation.metric_id == metric_id,
        FactObservation.obs_date == baseline_date
    ).subquery()
    
    # 根据rank_by选择不同的计算逻辑
    if rank_by == "delta":
        # 计算差值：latest - baseline
        query = db.query(
            latest_subq.c.dim_id,
            dim_name_col.label('dim_name'),
            latest_subq.c.latest_value,
            baseline_subq.c.baseline_value,
            (latest_subq.c.latest_value - baseline_subq.c.baseline_value).label('delta')
        ).join(
            dim_table, latest_subq.c.dim_id == dim_table.id
        ).outerjoin(
            baseline_subq, latest_subq.c.dim_id == baseline_subq.c.dim_id
        ).filter(
            latest_subq.c.latest_value.isnot(None),
            baseline_subq.c.baseline_value.isnot(None)
        ).order_by(desc('delta')).limit(topk)
        
        results = query.all()
        
        items = []
        for idx, row in enumerate(results, 1):
            items.append({
                "dimension_id": row.dim_id,
                "dimension_name": row.dim_name,
                "latest_value": float(row.latest_value) if row.latest_value else None,
                "baseline_value": float(row.baseline_value) if row.baseline_value else None,
                "delta": float(row.delta) if row.delta else None,
                "rank": idx
            })
    
    elif rank_by == "pct_change":
        # 计算百分比变化：(latest - baseline) / abs(baseline)
        query = db.query(
            latest_subq.c.dim_id,
            dim_name_col.label('dim_name'),
            latest_subq.c.latest_value,
            baseline_subq.c.baseline_value,
            case(
                (baseline_subq.c.baseline_value != 0, 
                 (latest_subq.c.latest_value - baseline_subq.c.baseline_value) / func.abs(baseline_subq.c.baseline_value)),
                else_=None
            ).label('pct_change')
        ).join(
            dim_table, latest_subq.c.dim_id == dim_table.id
        ).outerjoin(
            baseline_subq, latest_subq.c.dim_id == baseline_subq.c.dim_id
        ).filter(
            latest_subq.c.latest_value.isnot(None),
            baseline_subq.c.baseline_value.isnot(None),
            baseline_subq.c.baseline_value != 0
        ).order_by(desc('pct_change')).limit(topk)
        
        results = query.all()
        
        items = []
        for idx, row in enumerate(results, 1):
            delta = row.latest_value - row.baseline_value if row.latest_value and row.baseline_value else None
            items.append({
                "dimension_id": row.dim_id,
                "dimension_name": row.dim_name,
                "latest_value": float(row.latest_value) if row.latest_value else None,
                "baseline_value": float(row.baseline_value) if row.baseline_value else None,
                "delta": float(delta) if delta else None,
                "pct_change": float(row.pct_change) if row.pct_change else None,
                "rank": idx
            })
    
    elif rank_by == "streak":
        # 连续上涨/下跌天数（仅日度数据）
        # 需要查询最近N天的数据，计算连续趋势
        # 简化实现：查询最近window_days天的数据，计算连续同向变化天数
        # 注意：这需要metric的freq为daily
        
        # 查询最近window_days天的所有数据
        start_date = latest_date - timedelta(days=window_days)
        
        all_data = db.query(
            dim_id_col.label('dim_id'),
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_id,
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= latest_date,
            dim_id_col.isnot(None)
        ).order_by(
            dim_id_col, FactObservation.obs_date
        ).all()
        
        # 按维度分组，计算连续趋势
        dim_data = defaultdict(list)
        for row in all_data:
            dim_data[row.dim_id].append((row.obs_date, row.value))
        
        items = []
        for dim_id, values in dim_data.items():
            if len(values) < 2:
                continue
            
            # 计算连续上涨/下跌天数
            streak_days = 0
            direction = None  # 'up' or 'down'
            
            # 从最新日期往前遍历
            sorted_values = sorted(values, key=lambda x: x[0], reverse=True)
            for i in range(len(sorted_values) - 1):
                curr_val = sorted_values[i][1]
                prev_val = sorted_values[i + 1][1]
                
                if curr_val is None or prev_val is None:
                    break
                
                if curr_val > prev_val:
                    if direction == 'down':
                        break  # 方向改变，停止计数
                    direction = 'up'
                    streak_days += 1
                elif curr_val < prev_val:
                    if direction == 'up':
                        break  # 方向改变，停止计数
                    direction = 'down'
                    streak_days += 1
                else:
                    break  # 相等，停止计数
            
            if streak_days > 0:
                # 获取维度名称
                dim_obj = db.query(dim_table).filter(dim_table.id == dim_id).first()
                if dimension == "geo":
                    dim_name = dim_obj.province if dim_obj else str(dim_id)
                elif dimension == "company":
                    dim_name = dim_obj.company_name if dim_obj else str(dim_id)
                elif dimension == "warehouse":
                    dim_name = dim_obj.warehouse_name if dim_obj else str(dim_id)
                else:
                    dim_name = str(dim_id)
                
                latest_val = sorted_values[0][1]
                baseline_val = sorted_values[-1][1] if len(sorted_values) > 1 else None
                
                items.append({
                    "dimension_id": dim_id,
                    "dimension_name": dim_name,
                    "latest_value": float(latest_val) if latest_val else None,
                    "baseline_value": float(baseline_val) if baseline_val else None,
                    "streak_days": streak_days,
                    "streak_direction": direction,
                    "rank": 0  # 稍后排序
                })
        
        # 按streak_days降序排序
        items.sort(key=lambda x: x["streak_days"], reverse=True)
        items = items[:topk]
        for idx, item in enumerate(items, 1):
            item["rank"] = idx
    
    elif rank_by == "seasonal_percentile":
        # 基于seasonality的历史分位（近5年同周/同日）
        # 这需要调用seasonality_service的逻辑
        # 简化实现：查询历史同期的数据，计算分位
        from app.services.seasonality_service import query_seasonality
        
        # 获取当前日期在同年的周序号或月-日
        from datetime import datetime
        current_week = latest_date.isocalendar()[1]
        current_month_day = f"{latest_date.month:02d}-{latest_date.day:02d}"
        
        # 查询近5年的同期数据
        years = [latest_date.year - i for i in range(5)]
        
        try:
            seasonality_result = query_seasonality(
                db=db,
                metric_id=metric_id,
                years=years,
                filters=filters,
                x_mode="week_of_year",
                agg="mean"
            )
            
            # 从seasonality数据中提取当前周的数据
            # 这里简化处理，实际需要更复杂的逻辑
            items = []  # TODO: 实现seasonal_percentile的完整逻辑
            
        except Exception as e:
            # 如果seasonality查询失败，返回空结果
            items = []
    
    else:
        raise ValueError(f"Unsupported rank_by: {rank_by}")
    
    return {
        "metric_id": metric_id,
        "metric_name": metric_name,
        "dimension": dimension,
        "rank_by": rank_by,
        "window_days": window_days,
        "items": items
    }
