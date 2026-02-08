"""
检查raw_table中是否有2026年的原始数据
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

def check_raw_table_2026():
    """检查raw_table中是否有2026年的原始数据"""
    print("=" * 80)
    print("检查raw_table中是否有2026年的原始数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"集团企业全国"sheet
        enterprise_sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "集团企业全国"
        ).first()
        
        if not enterprise_sheet:
            print("\n未找到'集团企业全国'sheet")
            return
        
        # 查找raw_table
        raw_table = db.query(RawTable).filter(
            RawTable.raw_sheet_id == enterprise_sheet.id
        ).first()
        
        if not raw_table or not raw_table.table_json:
            print("\n未找到raw_table数据")
            return
        
        table_data = raw_table.table_json
        
        # 检查所有数据，查找包含2026的行
        print(f"\n查找包含'2026'的数据:")
        found_2026 = False
        for row_idx, row in enumerate(table_data):
            if isinstance(row, list):
                for cell in row:
                    if isinstance(cell, dict):
                        value = cell.get('value')
                        if value and '2026' in str(value):
                            print(f"  行{row_idx}, col={cell.get('col')}, row={cell.get('row')}, value={value}")
                            found_2026 = True
        
        if not found_2026:
            print("  未找到包含'2026'的数据")
        
        # 检查所有col=1（日期列）的值
        print(f"\n检查所有日期列（col=1）的值:")
        date_values = []
        for row in table_data:
            if isinstance(row, list):
                for cell in row:
                    if isinstance(cell, dict) and cell.get('col') == 1:
                        date_values.append({
                            'row': cell.get('row'),
                            'value': cell.get('value'),
                            'data_type': cell.get('data_type')
                        })
        
        # 按row排序
        date_values.sort(key=lambda x: x['row'])
        
        print(f"  找到 {len(date_values)} 个日期值")
        print(f"  最后10个日期值:")
        for dv in date_values[-10:]:
            print(f"    row={dv['row']}, value={dv['value']}, type={dv['data_type']}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_raw_table_2026()
