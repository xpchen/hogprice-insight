"""
分析E3. 供需曲线数据源
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import json

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

def analyze_data_sources():
    """分析数据源"""
    print("=" * 80)
    print("分析E3. 供需曲线数据源")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 定点屠宰数据
        print("\n1. 定点屠宰数据（用于图表1）:")
        # 查找屠宰相关的指标
        slaughter_metrics = db.query(DimMetric).filter(
            DimMetric.raw_header.like('%屠宰%')
        ).limit(5).all()
        
        print(f"  找到 {len(slaughter_metrics)} 个屠宰相关指标")
        for m in slaughter_metrics[:3]:
            print(f"    - {m.metric_name} ({m.raw_header})")
            count = db.query(FactObservation).filter(
                FactObservation.metric_id == m.id
            ).count()
            print(f"      数据条数: {count}")
        
        # 2. 钢联全国猪价月度均值
        print("\n\n2. 钢联全国猪价数据（用于图表1）:")
        price_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name.like('%钢联%'),
            DimMetric.raw_header.like('%全国%'),
            DimMetric.raw_header.like('%价%')
        ).limit(5).all()
        
        print(f"  找到 {len(price_metrics)} 个钢联全国价格指标")
        for m in price_metrics[:3]:
            print(f"    - {m.metric_name} ({m.raw_header})")
            count = db.query(FactObservation).filter(
                FactObservation.metric_id == m.id
            ).count()
            print(f"      数据条数: {count}")
        
        # 3. NYB数据（能繁母猪存栏和新生仔猪）
        print("\n\n3. NYB数据（用于图表2和图表3）:")
        nyb_sheets = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name.like('%NYB%')
        ).all()
        
        if nyb_sheets:
            for sheet in nyb_sheets:
                print(f"\n  找到sheet: {sheet.sheet_name}")
                print(f"    文件: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
                
                raw_table = db.query(RawTable).filter(
                    RawTable.raw_sheet_id == sheet.id
                ).first()
                
                if raw_table:
                    table_data = raw_table.table_json
                    if isinstance(table_data, str):
                        table_data = json.loads(table_data)
                    
                    print(f"    表格尺寸: {len(table_data)} 行 x {len(table_data[0]) if table_data else 0} 列")
                    
                    # 检查C列（能繁母猪）和G列（新生仔猪）
                    if len(table_data) > 1:
                        print(f"    前5行数据（检查C列和G列）:")
                        for idx, row in enumerate(table_data[:5]):
                            c_val = row[2] if len(row) > 2 else None  # C列（索引2）
                            g_val = row[6] if len(row) > 6 else None  # G列（索引6）
                            print(f"      行{idx+1}: C列={c_val}, G列={g_val}")
        else:
            print("  ✗ 未找到NYB sheet")
        
        # 4. 查找2020年1月的数据（作为基准）
        print("\n\n4. 查找2020年1月的数据（基准点）:")
        # 查找2020-01的数据
        obs_2020_01 = db.query(FactObservation).filter(
            FactObservation.obs_date >= '2020-01-01',
            FactObservation.obs_date < '2020-02-01'
        ).limit(5).all()
        
        print(f"  找到 {len(obs_2020_01)} 条2020年1月的数据")
        
    finally:
        db.close()

if __name__ == "__main__":
    analyze_data_sources()
