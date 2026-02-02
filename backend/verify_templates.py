"""
验证模板是否成功入库
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.chart_template import ChartTemplate


def verify_templates():
    """验证模板"""
    db = SessionLocal()
    try:
        templates = db.query(ChartTemplate).filter(ChartTemplate.is_public == True).all()
        
        print(f"Found {len(templates)} public templates in database:\n")
        
        for t in templates:
            spec = t.spec_json
            template_id = spec.get("template_id", "N/A")
            category = spec.get("category", "N/A")
            
            print(f"ID: {t.id:4d} | Template: {template_id:4s} | Category: {category:10s} | Name: {t.name}")
        
        print(f"\n{'='*80}")
        print("Template verification completed!")
        
        if len(templates) >= 8:
            print("✓ All 8 preset templates are in database")
        else:
            print(f"⚠ Only {len(templates)} templates found, expected 8")
    
    finally:
        db.close()


if __name__ == "__main__":
    verify_templates()
