"""
详细检查E2数据
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

def check_data():
    """检查数据"""
    db: Session = SessionLocal()
    try:
        raw_file = db.query(RawFile).filter(
            RawFile.filename == "2、【生猪产业数据】.xlsx"
        ).first()
        
        if not raw_file:
            print("文件未找到")
            return
        
        # 检查NYB数据
        print("=" * 80)
        print("检查NYB数据（查看有值的行）")
        print("=" * 80)
        sheet = db.query(RawSheet).filter(
            RawSheet.raw_file_id == raw_file.id,
            RawSheet.sheet_name == "NYB"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(RawTable.raw_sheet_id == sheet.id).first()
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"\n总行数: {len(table_data)}")
                print(f"\n查找有值的行（C列能繁环比、G列新生仔猪环比、Q列存栏环比）:")
                count = 0
                for row_idx, row in enumerate(table_data[2:], start=3):
                    if len(row) < 17:
                        continue
                    
                    # 检查是否有值
                    c_val = row[2] if len(row) > 2 else None
                    g_val = row[6] if len(row) > 6 else None
                    q_val = row[16] if len(row) > 16 else None
                    
                    if c_val is not None or g_val is not None or q_val is not None:
                        count += 1
                        date_val = row[1] if len(row) > 1 else None
                        print(f"\n  行{row_idx}: 日期={date_val}")
                        if c_val is not None:
                            print(f"    C列(能繁环比-全国): {c_val}")
                        if g_val is not None:
                            print(f"    G列(新生仔猪环比-全国): {g_val}")
                        if q_val is not None:
                            print(f"    Q列(存栏环比): {q_val}")
                        
                        if count >= 10:
                            break
        
        # 检查协会猪料数据
        print("\n\n" + "=" * 80)
        print("检查协会猪料数据（查看有值的行）")
        print("=" * 80)
        sheet = db.query(RawSheet).filter(
            RawSheet.raw_file_id == raw_file.id,
            RawSheet.sheet_name == "02.协会猪料"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(RawTable.raw_sheet_id == sheet.id).first()
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"\n总行数: {len(table_data)}")
                print(f"\n查找有值的行（I列母猪料环比、N列仔猪料环比、S列育肥料环比）:")
                count = 0
                for row_idx, row in enumerate(table_data[1:], start=2):
                    if len(row) < 19:
                        continue
                    
                    i_val = row[8] if len(row) > 8 else None
                    n_val = row[13] if len(row) > 13 else None
                    s_val = row[18] if len(row) > 18 else None
                    
                    if i_val is not None or n_val is not None or s_val is not None:
                        count += 1
                        date_val = row[1] if len(row) > 1 else None
                        print(f"\n  行{row_idx}: 日期={date_val}")
                        if i_val is not None:
                            print(f"    I列(母猪料环比): {i_val}")
                        if n_val is not None:
                            print(f"    N列(仔猪料环比): {n_val}")
                        if s_val is not None:
                            print(f"    S列(育肥料环比): {s_val}")
                        
                        if count >= 10:
                            break
        
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
