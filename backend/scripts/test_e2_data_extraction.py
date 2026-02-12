"""
测试E2数据提取
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import json
from datetime import datetime

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

def test_extraction():
    """测试数据提取"""
    db: Session = SessionLocal()
    try:
        # 查找文件
        raw_file = db.query(RawFile).filter(
            RawFile.filename == "2、【生猪产业数据】.xlsx"
        ).first()
        
        if not raw_file:
            print("文件未找到")
            return
        
        print("=" * 80)
        print("测试E2数据提取")
        print("=" * 80)
        
        # 1. 测试NYB数据提取
        print("\n1. NYB sheet数据:")
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
                
                print(f"  数据行数: {len(table_data)}")
                if len(table_data) > 2:
                    print(f"  第2行（表头）: {table_data[1][:10]}")
                    print(f"  第3行（数据）: {table_data[2][:10]}")
                    # B列是日期（索引1），C列是能繁环比-全国（索引2），G列是新生仔猪环比-全国（索引6），Q列是存栏环比（索引16）
                    if len(table_data[2]) > 16:
                        print(f"    B列(日期): {table_data[2][1]}")
                        print(f"    C列(能繁环比-全国): {table_data[2][2]}")
                        print(f"    G列(新生仔猪环比-全国): {table_data[2][6]}")
                        print(f"    Q列(存栏环比): {table_data[2][16]}")
        
        # 2. 测试协会猪料数据提取
        print("\n2. 02.协会猪料 sheet数据:")
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
                
                print(f"  数据行数: {len(table_data)}")
                if len(table_data) > 2:
                    print(f"  第1行（表头）: {table_data[0][:10]}")
                    print(f"  第3行（数据）: {table_data[2][:20]}")
                    # B列是日期（索引1），I列是母猪料环比（索引8），N列是仔猪料环比（索引13），S列是育肥料环比（索引18）
                    if len(table_data[2]) > 18:
                        print(f"    B列(日期): {table_data[2][1]}")
                        print(f"    I列(母猪料环比): {table_data[2][8]}")
                        print(f"    N列(仔猪料环比): {table_data[2][13]}")
                        print(f"    S列(育肥料环比): {table_data[2][18]}")
        
        # 3. 测试涌益数据提取
        print("\n3. 涌益 sheet数据:")
        sheet = db.query(RawSheet).filter(
            RawSheet.raw_file_id == raw_file.id,
            RawSheet.sheet_name == "涌益"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(RawTable.raw_sheet_id == sheet.id).first()
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"  数据行数: {len(table_data)}")
                if len(table_data) > 2:
                    print(f"  第2行（表头）: {table_data[1][:15]}")
                    print(f"  第3行（数据）: {table_data[2][:15]}")
                    # A列是日期（索引0），E列是能繁母猪（索引4），F列是环比（索引5），P列是新生仔猪（索引15），Q列是环比（索引16），W列是存栏（索引22），X列是环比（索引23）
                    if len(table_data[2]) > 23:
                        print(f"    A列(日期): {table_data[2][0]}")
                        print(f"    E列(能繁母猪): {table_data[2][4]}, F列(环比): {table_data[2][5]}")
                        print(f"    P列(新生仔猪): {table_data[2][15]}, Q列(环比): {table_data[2][16]}")
                        print(f"    W列(存栏): {table_data[2][22]}, X列(环比): {table_data[2][23]}")
        
        # 4. 测试钢联数据提取
        print("\n4. 4.1.钢联数据 sheet数据:")
        sheet = db.query(RawSheet).filter(
            RawSheet.raw_file_id == raw_file.id,
            RawSheet.sheet_name == "4.1.钢联数据"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(RawTable.raw_sheet_id == sheet.id).first()
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"  数据行数: {len(table_data)}")
                if len(table_data) > 2:
                    print(f"  第1行（表头）: {table_data[0][:15]}")
                    print(f"  第3行（数据）: {table_data[2][:15]}")
                    # A列是日期（索引0），B列是存栏环比-中国（索引1），L列是能繁存栏环比（索引11），O列是新生仔猪数环比（索引14），S列是育肥料环比（索引18），W列是仔猪饲料环比（索引22），AA列是母猪料环比（索引26）
                    if len(table_data[2]) > 26:
                        print(f"    A列(日期): {table_data[2][0]}")
                        print(f"    B列(存栏环比-中国): {table_data[2][1]}")
                        print(f"    L列(能繁存栏环比): {table_data[2][11]}")
                        print(f"    O列(新生仔猪数环比): {table_data[2][14]}")
                        print(f"    S列(育肥料环比): {table_data[2][18]}")
                        print(f"    W列(仔猪饲料环比): {table_data[2][22]}")
                        print(f"    AA列(母猪料环比): {table_data[2][26]}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_extraction()
