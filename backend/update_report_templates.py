"""
更新现有报告模板，重新解析metric_code为metric_id
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.models.report_template import ReportTemplate
from app.models.metric_code_map import resolve_metric_id

db = SessionLocal()
try:
    templates = db.query(ReportTemplate).all()
    print(f"Found {len(templates)} templates to update\n")
    
    for template in templates:
        print(f"Updating template: {template.name}")
        template_json = template.template_json
        updated = False
        
        sheets = template_json.get("sheets", [])
        for sheet in sheets:
            # 处理seasonality类型的sheet
            if sheet.get("chart_type") == "seasonality":
                metric_code = sheet.get("metric_code")
                if metric_code and not sheet.get("metric_id"):
                    metric_id = resolve_metric_id(db, metric_code)
                    if metric_id:
                        sheet["metric_id"] = metric_id
                        updated = True
                        print(f"  Resolved {metric_code} -> metric_id={metric_id}")
            
            # 处理timeseries类型的sheet
            elif sheet.get("chart_type") == "timeseries":
                # 处理metrics数组
                if "metrics" in sheet and isinstance(sheet["metrics"], list):
                    resolved_metric_ids = []
                    for metric_config in sheet["metrics"]:
                        metric_code = metric_config.get("metric_code")
                        if metric_code and not metric_config.get("metric_id"):
                            metric_id = resolve_metric_id(db, metric_code)
                            if metric_id:
                                metric_config["metric_id"] = metric_id
                                resolved_metric_ids.append(metric_id)
                                updated = True
                                print(f"  Resolved {metric_code} -> metric_id={metric_id}")
                        elif metric_config.get("metric_id"):
                            resolved_metric_ids.append(metric_config["metric_id"])
                    
                    # 设置metric_ids数组以便兼容
                    if resolved_metric_ids:
                        sheet["metric_ids"] = resolved_metric_ids
                        updated = True
                
                # 处理单个metric_code
                metric_code = sheet.get("metric_code")
                if metric_code and not sheet.get("metric_id"):
                    metric_id = resolve_metric_id(db, metric_code)
                    if metric_id:
                        sheet["metric_id"] = metric_id
                        updated = True
                        print(f"  Resolved {metric_code} -> metric_id={metric_id}")
        
        if updated:
            template.template_json = template_json
            print(f"  Template updated successfully\n")
        else:
            print(f"  No updates needed\n")
    
    db.commit()
    print("All templates updated successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
