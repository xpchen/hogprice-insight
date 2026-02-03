"""检查表是否存在"""
import sys
import os
import io

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from sqlalchemy import inspect, text

def check_table(table_name: str):
    db = SessionLocal()
    try:
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if table_name in tables:
            print(f"[OK] 表 {table_name} 存在")
            
            # 显示表结构
            columns = inspector.get_columns(table_name)
            print(f"\n表结构:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
            
            # 显示记录数
            result = db.execute(text(f"SELECT COUNT(*) as cnt FROM `{table_name}`"))
            row = result.fetchone()
            count = row[0] if row else 0
            print(f"\n记录数: {count}")
        else:
            print(f"[ERROR] 表 {table_name} 不存在")
            print(f"\n可用表（包含'weight'的）:")
            weight_tables = [t for t in tables if 'weight' in t.lower()]
            for t in weight_tables:
                print(f"  - {t}")
    finally:
        db.close()

if __name__ == "__main__":
    check_table("yongyi_weekly_weight_split")
