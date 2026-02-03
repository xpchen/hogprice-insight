"""
初始化常用报告模板到数据库
"""
import sys
import io
import json
from pathlib import Path

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.report_template import ReportTemplate
from app.models.metric_code_map import resolve_metric_id


def load_report_templates():
    """加载报告模板JSON文件"""
    json_path = Path(__file__).parent.parent / "data" / "report_templates.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_metric_codes_in_template(template_json: dict, db: Session):
    """解析模板中的metric_code为metric_id"""
    resolved = json.loads(json.dumps(template_json))  # 深拷贝
    
    sheets = resolved.get("sheets", [])
    for sheet in sheets:
        # 处理seasonality类型的sheet
        if sheet.get("chart_type") == "seasonality":
            metric_code = sheet.get("metric_code")
            if metric_code:
                metric_id = resolve_metric_id(db, metric_code)
                if metric_id:
                    sheet["metric_id"] = metric_id
                    print(f"  Resolved {metric_code} -> metric_id={metric_id}")
                else:
                    print(f"  WARNING: Could not resolve metric_code {metric_code}")
        
        # 处理timeseries类型的sheet
        elif sheet.get("chart_type") == "timeseries":
            # 处理metric_ids数组
            if "metric_ids" in sheet and isinstance(sheet["metric_ids"], list):
                resolved_ids = []
                for code in sheet["metric_ids"]:
                    if isinstance(code, str):
                        metric_id = resolve_metric_id(db, code)
                        if metric_id:
                            resolved_ids.append(metric_id)
                if resolved_ids:
                    sheet["metric_ids"] = resolved_ids
            
            # 处理metrics数组（双轴或多指标）
            if "metrics" in sheet and isinstance(sheet["metrics"], list):
                resolved_metric_ids = []
                for metric_config in sheet["metrics"]:
                    metric_code = metric_config.get("metric_code")
                    if metric_code:
                        metric_id = resolve_metric_id(db, metric_code)
                        if metric_id:
                            metric_config["metric_id"] = metric_id
                            resolved_metric_ids.append(metric_id)
                            print(f"  Resolved {metric_code} -> metric_id={metric_id}")
                        else:
                            print(f"  WARNING: Could not resolve metric_code {metric_code}")
                    elif "metric_id" in metric_config:
                        resolved_metric_ids.append(metric_config["metric_id"])
                
                # 如果解析成功，也设置metric_ids数组以便兼容
                if resolved_metric_ids:
                    sheet["metric_ids"] = resolved_metric_ids
            
            # 处理单个metric_code
            metric_code = sheet.get("metric_code")
            if metric_code:
                metric_id = resolve_metric_id(db, metric_code)
                if metric_id:
                    sheet["metric_id"] = metric_id
                    print(f"  Resolved {metric_code} -> metric_id={metric_id}")
    
    return resolved


def init_report_templates_to_db(db: Session, owner_id: int = None):
    """初始化报告模板到数据库"""
    templates = load_report_templates()
    
    print(f"Loading {len(templates)} report templates...")
    
    for template_data in templates:
        name = template_data["name"]
        template_json = template_data["template_json"]
        is_public = template_data.get("is_public", True)
        
        print(f"\nProcessing template: {name}")
        
        # 检查是否已存在同名模板
        existing = db.query(ReportTemplate).filter(ReportTemplate.name == name).first()
        if existing:
            print(f"  Template '{name}' already exists, skipping...")
            continue
        
        # 解析metric_code为metric_id
        resolved_json = resolve_metric_codes_in_template(template_json, db)
        
        # 创建模板记录
        new_template = ReportTemplate(
            name=name,
            template_json=resolved_json,
            is_public=is_public,
            owner_id=owner_id
        )
        
        db.add(new_template)
        print(f"  Added template: {name}")
    
    db.commit()
    print(f"\nSuccessfully initialized {len(templates)} report templates!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        # 获取系统管理员用户ID（假设ID为1）
        from app.models.sys_user import SysUser
        admin_user = db.query(SysUser).filter(SysUser.username == "admin").first()
        owner_id = admin_user.id if admin_user else None
        
        init_report_templates_to_db(db, owner_id=owner_id)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
