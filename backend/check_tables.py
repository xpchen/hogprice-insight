"""
检查数据库表是否存在
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import inspect
from app.core.database import engine, Base
from app.models import *

def check_tables():
    """检查所有表是否存在"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print("=" * 60)
    print("Checking database tables...")
    print("=" * 60)
    print(f"\nExisting tables ({len(existing_tables)}):")
    for table in sorted(existing_tables):
        print(f"  ✓ {table}")
    
    # 检查需要的表
    required_tables = [
        'sys_user',
        'sys_role',
        'sys_user_role',
        'import_batch',
        'dim_metric',
        'dim_geo',
        'dim_company',
        'dim_warehouse',
        'fact_observation'
    ]
    
    print(f"\nRequired tables ({len(required_tables)}):")
    missing_tables = []
    for table in required_tables:
        if table in existing_tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} - MISSING!")
            missing_tables.append(table)
    
    if missing_tables:
        print(f"\n❌ Missing {len(missing_tables)} table(s): {', '.join(missing_tables)}")
        print("\nPlease run one of the following:")
        print("  1. alembic upgrade head")
        print("  2. Or execute init_all_tables.sql")
        return False
    else:
        print("\n✅ All required tables exist!")
        return True

if __name__ == "__main__":
    success = check_tables()
    sys.exit(0 if success else 1)
