"""验证数据库表是否已创建"""
import sys
import os
import io

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect
from app.core.database import engine

# 需要检查的表
required_tables = [
    'dim_indicator',
    'dim_region',
    'dim_contract',
    'dim_option',
    'fact_indicator_ts',
    'fact_indicator_metrics',
    'fact_futures_daily',
    'fact_options_daily',
    'ingest_error',
    'ingest_mapping'
]

def main():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print("检查数据库表...")
    print("=" * 50)
    
    all_ok = True
    for table in required_tables:
        if table in existing_tables:
            print(f"✓ {table}")
        else:
            print(f"✗ {table} - 未找到！")
            all_ok = False
    
    print("=" * 50)
    
    # 检查import_batch表的扩展字段
    if 'import_batch' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('import_batch')]
        required_columns = ['source_code', 'date_range', 'mapping_json']
        
        print("\n检查 import_batch 表扩展字段...")
        for col in required_columns:
            if col in columns:
                print(f"✓ import_batch.{col}")
            else:
                print(f"✗ import_batch.{col} - 未找到！")
                all_ok = False
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✓ 所有表都已创建成功！")
    else:
        print("✗ 部分表缺失，请检查迁移日志")
    
    return all_ok

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
