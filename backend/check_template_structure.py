"""
检查模板的实际结构
"""
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.chart_template import ChartTemplate


def check_structure():
    """检查模板结构"""
    db = SessionLocal()
    try:
        template = db.query(ChartTemplate).filter(ChartTemplate.name == "标肥价差季节性").first()
        
        if template:
            print("Template structure:")
            print(json.dumps(template.spec_json, indent=2, ensure_ascii=False))
        else:
            print("Template not found")
    
    finally:
        db.close()


if __name__ == "__main__":
    check_structure()
