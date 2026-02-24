"""Initialize dim_source data"""
import sys
import os
import io

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.dim_source import DimSource


def init_dim_source_data():
    """插入初始数据源数据"""
    db = SessionLocal()
    try:
        sources = [
            {
                "source_code": "YONGYI",
                "source_name": "涌益咨询",
                "update_freq": "daily,weekly",
                "source_type": "vendor",
                "license_note": "涌益咨询数据，需授权使用"
            },
            {
                "source_code": "MYSTEEL",
                "source_name": "钢联数据",
                "update_freq": "daily",
                "source_type": "vendor",
                "license_note": "钢联数据，需授权使用"
            },
            {
                "source_code": "DCE",
                "source_name": "大连商品交易所",
                "update_freq": "daily",
                "source_type": "exchange",
                "license_note": "公开数据"
            },
            {
                "source_code": "GANGLIAN",
                "source_name": "钢联数据（别名）",
                "update_freq": "daily",
                "source_type": "vendor",
                "license_note": "钢联数据，需授权使用"
            },
            {
                "source_code": "LEGACY",
                "source_name": "旧系统数据",
                "update_freq": "irregular",
                "source_type": "legacy",
                "license_note": "历史迁移数据"
            },
            {
                "source_code": "ENTERPRISE",
                "source_name": "集团企业出栏跟踪",
                "update_freq": "daily,monthly",
                "source_type": "vendor",
                "license_note": "集团企业出栏数据"
            },
            {
                "source_code": "WHITE_STRIP_MARKET",
                "source_name": "白条市场跟踪",
                "update_freq": "daily",
                "source_type": "vendor",
                "license_note": "白条到货量及价格"
            }
        ]
        
        for source_data in sources:
            existing = db.query(DimSource).filter(DimSource.source_code == source_data["source_code"]).first()
            if existing:
                # 更新现有记录
                for key, value in source_data.items():
                    setattr(existing, key, value)
                print(f"Updated source: {source_data['source_code']}")
            else:
                # Insert new record
                source = DimSource(**source_data)
                db.add(source)
                print(f"Inserted source: {source_data['source_code']}")
        
        db.commit()
        print("Source initialization completed")
        
    except Exception as e:
        db.rollback()
        print(f"Initialization failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_dim_source_data()
