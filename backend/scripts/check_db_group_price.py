"""
检查数据库中集团价格相关的数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def check_group_price_data():
    """检查集团价格数据"""
    print("=" * 80)
    print("检查数据库中集团价格相关的数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 检查"集团企业出栏价"sheet
        print("\n1. 检查'集团企业出栏价'sheet:")
        ganglian_sheet = db.query(RawSheet).join(RawFile).filter(
            RawFile.filename.like('%钢联%'),
            RawSheet.sheet_name == "集团企业出栏价"
        ).first()
        
        if ganglian_sheet:
            print(f"  找到sheet: {ganglian_sheet.sheet_name}")
            print(f"  文件: {ganglian_sheet.raw_file.filename if ganglian_sheet.raw_file else 'N/A'}")
            
            # 检查是否有对应的指标
            metrics = db.query(DimMetric).filter(
                DimMetric.sheet_name == "集团企业出栏价"
            ).limit(10).all()
            
            if metrics:
                print(f"  找到 {len(metrics)} 个相关指标:")
                for m in metrics:
                    print(f"    - {m.metric_name} (原始表头: {m.raw_header})")
            else:
                print("  未找到相关指标，可能需要从raw_table读取")
        else:
            print("  未找到'集团企业出栏价'sheet")
        
        # 2. 检查"白条市场"sheet
        print("\n2. 检查'白条市场'sheet:")
        white_strip_sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "白条市场"
        ).first()
        
        if white_strip_sheet:
            print(f"  找到sheet: {white_strip_sheet.sheet_name}")
            print(f"  文件: {white_strip_sheet.raw_file.filename if white_strip_sheet.raw_file else 'N/A'}")
        else:
            print("  未找到'白条市场'sheet")
            
            # 查找包含"白条"的sheet
            white_strip_sheets = db.query(RawSheet).filter(
                RawSheet.sheet_name.like('%白条%')
            ).all()
            if white_strip_sheets:
                print(f"  找到 {len(white_strip_sheets)} 个包含'白条'的sheet:")
                for s in white_strip_sheets:
                    print(f"    - {s.sheet_name} (文件: {s.raw_file.filename if s.raw_file else 'N/A'})")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_group_price_data()
