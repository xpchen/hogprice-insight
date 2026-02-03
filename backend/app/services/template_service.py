"""
模板服务：加载和管理8套客户常用模板
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.metric_code_map import resolve_metric_id


def load_templates() -> List[Dict]:
    """加载模板配置"""
    template_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "templates.json"
    )
    
    with open(template_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_template(template_id: str) -> Optional[Dict]:
    """获取指定模板"""
    templates = load_templates()
    for template in templates:
        if template["template_id"] == template_id:
            return template
    return None


def resolve_template_params(template: Dict, user_params: Dict, db: Session) -> Dict:
    """
    解析模板参数，将占位符替换为实际值
    
    Args:
        template: 模板配置
        user_params: 用户提供的参数
        db: 数据库会话
    
    Returns:
        解析后的参数
    """
    resolved = {}
    
    # 处理默认值
    for param_name, param_config in template.get("params", {}).items():
        if param_name in user_params:
            resolved[param_name] = user_params[param_name]
        else:
            default = param_config.get("default")
            if default == "YTD":
                # 本年迄今
                today = datetime.now()
                resolved[param_name] = {
                    "start": f"{today.year}-01-01",
                    "end": today.strftime("%Y-%m-%d")
                }
            elif default == "last_90_days":
                # 最近90天
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                resolved[param_name] = {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                }
            elif default == "last_180_days":
                # 最近180天
                end_date = datetime.now()
                start_date = end_date - timedelta(days=180)
                resolved[param_name] = {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                }
            elif default == "top10" or default == "top5":
                # TopN选择（需要后续处理）
                resolved[param_name] = default
            elif isinstance(default, list):
                # 默认年份列表（最近6年）
                if not default and param_name == "years":
                    current_year = datetime.now().year
                    resolved[param_name] = list(range(current_year - 5, current_year + 1))
                else:
                    resolved[param_name] = default
            else:
                resolved[param_name] = default
    
    return resolved


def resolve_block_query(block: Dict, resolved_params: Dict, db: Session) -> Dict:
    """
    解析block的query配置，将metric_code转换为metric_id
    
    Args:
        block: block配置
        resolved_params: 已解析的参数
        db: 数据库会话
    
    Returns:
        解析后的query配置
    """
    query = block.get("query", {}).copy()
    
    # 处理metric_code -> metric_id
    if "metric_code" in query:
        metric_code = query["metric_code"]
        metric_id = resolve_metric_id(db, metric_code)
        if metric_id:
            query["metric_id"] = metric_id
            del query["metric_code"]
    
    # 处理metrics数组（双轴图）
    if "metrics" in query:
        for metric_config in query["metrics"]:
            if "metric_code" in metric_config:
                metric_code = metric_config["metric_code"]
                metric_id = resolve_metric_id(db, metric_code)
                if metric_id:
                    metric_config["metric_id"] = metric_id
                    del metric_config["metric_code"]
    
    # 替换参数占位符
    query_str = json.dumps(query)
    for param_name, param_value in resolved_params.items():
        placeholder = f"{{{{params.{param_name}}}}}"
        if placeholder in query_str:
            query_str = query_str.replace(placeholder, json.dumps(param_value))
    
    return json.loads(query_str)


def init_templates_to_db(db: Session):
    """
    将8套模板初始化到数据库（chart_template表）
    
    Args:
        db: 数据库会话
    """
    from app.models.chart_template import ChartTemplate
    
    templates = load_templates()
    
    for template_config in templates:
        # 检查是否已存在
        existing = db.query(ChartTemplate).filter(
            ChartTemplate.name == template_config["name"]
        ).first()
        
        if existing:
            continue
        
        # 构建spec_json（ChartSpec格式）
        spec_json = {
            "chart_type": template_config["chart_type"],
            "template_id": template_config["template_id"],
            "category": template_config["category"],
            "description": template_config.get("description", ""),
            "params": template_config.get("params", {}),
            "blocks": template_config.get("blocks", []),
            "export": template_config.get("export", {}),
            "acceptance": template_config.get("acceptance", [])
        }
        
        # 创建模板记录
        template = ChartTemplate(
            name=template_config["name"],
            chart_type=template_config["chart_type"],
            spec_json=spec_json,
            is_public=True,  # 8套模板设为公共模板
            owner_id=None  # 系统模板，无owner
        )
        
        db.add(template)
        print(f"Created template: {template_config['name']} ({template_config['template_id']})")
    
    db.commit()
    print(f"Success: Initialized {len(templates)} preset templates")
