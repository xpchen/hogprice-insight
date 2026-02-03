"""直接创建yongyi_weekly_weight_split表"""
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

def create_table():
    db = SessionLocal()
    try:
        inspector = inspect(db.bind)
        table_name = 'yongyi_weekly_weight_split'
        
        if table_name in inspector.get_table_names():
            print(f"[INFO] 表 {table_name} 已存在，跳过创建")
            return
        
        print(f"[INFO] 创建表 {table_name}...")
        
        # 创建表的SQL
        create_sql = """
        CREATE TABLE yongyi_weekly_weight_split (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            batch_id BIGINT,
            period_end DATE NOT NULL COMMENT '周期结束日期',
            nation_avg_weight DECIMAL(18, 6) COMMENT '全国均重',
            group_weight DECIMAL(18, 6) COMMENT '集团均重',
            scatter_weight DECIMAL(18, 6) COMMENT '散户均重',
            group_ratio DECIMAL(18, 6) COMMENT '集团占比',
            scatter_ratio DECIMAL(18, 6) COMMENT '散户占比',
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
            UNIQUE KEY uk_period (period_end),
            INDEX idx_batch (batch_id),
            INDEX idx_period (period_end)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        db.execute(text(create_sql))
        db.commit()
        
        print(f"[OK] 表 {table_name} 创建成功")
        
        # 验证表结构
        columns = inspector.get_columns(table_name)
        print(f"\n表结构:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 创建表失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_table()
