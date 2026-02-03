"""
模板执行服务：解析预设模板并执行查询
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.services.template_service import resolve_template_params, resolve_block_query
from app.services.seasonality_service import query_seasonality
from app.services.query_service import query_timeseries
from app.models.metric_code_map import resolve_metric_id


def execute_template(
    db: Session,
    template: Dict,
    user_params: Dict
) -> Dict:
    """
    执行模板，生成图表数据
    
    Args:
        db: 数据库会话
        template: 模板配置（从templates.json或数据库加载）
        user_params: 用户提供的参数
    
    Returns:
        包含所有blocks数据的字典，格式：
        {
            "blocks": {
                "block_id": {
                    "type": "seasonality|timeseries",
                    "data": {...} 或 "error": "..."
                }
            }
        }
    """
    # 解析参数
    resolved_params = resolve_template_params(template, user_params, db)
    
    # 执行所有blocks
    results = {}
    
    for block in template.get("blocks", []):
        block_id = block.get("block_id")
        block_type = block.get("type")
        
        if block_type == "seasonality":
            # 执行季节性查询
            query_config = resolve_block_query(block, resolved_params, db)
            
            # 确保metric_id存在
            if "metric_id" not in query_config:
                metric_code = query_config.get("metric_code")
                if metric_code:
                    metric_id = resolve_metric_id(db, metric_code)
                    if metric_id:
                        query_config["metric_id"] = metric_id
            
            if "metric_id" in query_config:
                years = query_config.get("years", [])
                if isinstance(years, str):
                    if years.startswith("{{"):
                        # 参数占位符，从resolved_params获取
                        years = resolved_params.get("years", [])
                    else:
                        # 尝试解析JSON
                        try:
                            import json
                            years = json.loads(years)
                        except:
                            years = []
                
                if not isinstance(years, list):
                    years = [years] if years else []
                
                # 如果没有年份，使用默认值（最近6年）
                if not years:
                    current_year = datetime.now().year
                    years = list(range(current_year - 5, current_year + 1))
            
                result = query_seasonality(
                    db=db,
                    metric_id=query_config["metric_id"],
                    years=years,
                    filters={
                        "geo_ids": query_config.get("geo_ids", []),
                        "company_ids": []
                    },
                    x_mode=query_config.get("x_mode", "week_of_year"),
                    agg=query_config.get("agg", "mean")
                )
                
                results[block_id] = {
                    "type": "seasonality",
                    "data": result
                }
            else:
                # metric_id缺失，无法执行
                results[block_id] = {
                    "type": "seasonality",
                    "error": f"Metric ID not found for metric_code: {query_config.get('metric_code', 'unknown')}"
                }
        
        elif block_type == "timeseries" or block_type == "timeseries_dual_axis" or block_type == "timeseries_multi_line":
            # 执行时间序列查询
            query_config = resolve_block_query(block, resolved_params, db)
            
            # 处理metric_ids
            metric_ids = []
            if "metric_id" in query_config:
                metric_ids = [query_config["metric_id"]]
            elif "metrics" in query_config:
                # 双轴或多指标
                for metric_config in query_config["metrics"]:
                    if "metric_id" in metric_config:
                        metric_ids.append(metric_config["metric_id"])
                    elif "metric_code" in metric_config:
                        metric_id = resolve_metric_id(db, metric_config["metric_code"])
                        if metric_id:
                            metric_ids.append(metric_id)
            
            if metric_ids:
                # 处理日期范围
                date_range = query_config.get("date_range")
                if isinstance(date_range, str) and date_range.startswith("{{"):
                    date_range = resolved_params.get("date_range")
                elif isinstance(date_range, str):
                    # 处理特殊值
                    if date_range == "YTD":
                        today = datetime.now()
                        date_range = {
                            "start": f"{today.year}-01-01",
                            "end": today.strftime("%Y-%m-%d")
                        }
                    elif date_range == "last_90_days":
                        end = datetime.now()
                        start = end - timedelta(days=90)
                        date_range = {
                            "start": start.strftime("%Y-%m-%d"),
                            "end": end.strftime("%Y-%m-%d")
                        }
                
                result = query_timeseries(
                    db=db,
                    date_range=date_range,
                    metric_ids=metric_ids,
                    geo_ids=query_config.get("geo_ids", []),
                    company_ids=query_config.get("company_ids", []),
                    time_dimension=query_config.get("time_dimension", "daily")
                )
                
                results[block_id] = {
                    "type": block_type,
                    "data": result,
                    "metrics_config": query_config.get("metrics", [])  # 保存axis配置
                }
            else:
                # metric_ids缺失，无法执行
                results[block_id] = {
                    "type": block_type,
                    "error": f"No valid metric IDs found for block {block_id}"
                }
        
        elif block_type == "summary":
            # 摘要统计（需要基于前面的查询结果）
            # 这里简化处理，实际应该基于前面的block结果计算
            results[block_id] = {
                "type": "summary",
                "data": {}  # 需要后续实现
            }
    
    return {
        "template_id": template.get("template_id"),
        "template_name": template.get("name"),
        "blocks": results
    }
