"""
验证报告模板是否成功创建
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.models.report_template import ReportTemplate

db = SessionLocal()
try:
    templates = db.query(ReportTemplate).all()
    print(f"Total report templates: {len(templates)}\n")
    
    for t in templates:
        print(f"ID: {t.id}")
        print(f"Name: {t.name}")
        print(f"Public: {t.is_public}")
        print(f"Owner ID: {t.owner_id}")
        print(f"Created: {t.created_at}")
        print(f"Sheets count: {len(t.template_json.get('sheets', []))}")
        print("-" * 50)
finally:
    db.close()
