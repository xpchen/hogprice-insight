"""
测试结构分析各个数据源的数据获取
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
from sqlalchemy import func, or_
from datetime import date, datetime, timedelta
import math

def _get_raw_table_data(db: Session, sheet_name: str, filename_pattern: str = None):
    """获取raw_table数据"""
    query = db.query(RawSheet).join(RawFile)
    
    if filename_pattern:
        query = query.filter(RawFile.filename.like(f'%{filename_pattern}%'))
    
    sheet = query.filter(RawSheet.sheet_name == sheet_name).first()
    
    if not sheet:
        return None
    
    raw_table = db.query(RawTable).filter(
        RawTable.raw_sheet_id == sheet.id
    ).first()
    
    if not raw_table:
        return None
    
    table_data = raw_table.table_json
    if isinstance(table_data, str):
        table_data = json.loads(table_data)
    
    return table_data

def _parse_excel_date(date_val):
    """解析Excel日期"""
    if isinstance(date_val, str):
        try:
            if 'T' in date_val:
                date_str = date_val.split('T')[0]
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date_str = date_val.split()[0] if ' ' in date_val else date_val
                return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            pass
    elif isinstance(date_val, (int, float)):
        try:
            excel_epoch = datetime(1899, 12, 30)
            return (excel_epoch + timedelta(days=int(date_val))).date()
        except:
            pass
    elif isinstance(date_val, date):
        return date_val
    elif hasattr(date_val, 'date'):
        return date_val.date()
    return None

def test_cr20():
    """测试CR20数据"""
    print("=" * 80)
    print("1. 测试CR20集团出栏环比")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"集团企业全国"sheet
        enterprise_sheet = db.query(RawSheet).join(RawFile).filter(
            RawFile.filename.like('%集团企业月度数据跟踪%'),
            RawSheet.sheet_name == "集团企业全国"
        ).first()
        
        if not enterprise_sheet:
            print("  ✗ 未找到'集团企业全国'sheet")
            return
        
        print(f"  ✓ 找到sheet: {enterprise_sheet.sheet_name}")
        
        raw_table = db.query(RawTable).filter(
            RawTable.raw_sheet_id == enterprise_sheet.id
        ).first()
        
        if not raw_table:
            print("  ✗ 未找到raw_table数据")
            return
        
        table_data = raw_table.table_json
        if isinstance(table_data, str):
            table_data = json.loads(table_data)
        
        print(f"  ✓ 找到数据，共{len(table_data)}行")
        
        # 检查是否有CR20数据
        cr20_count = 0
        for row in table_data:
            if isinstance(row, list):
                for cell in row:
                    if isinstance(cell, dict):
                        if cell.get('col') == 24 and cell.get('value') == 'CR20':
                            cr20_count += 1
        
        print(f"  ✓ 找到{cr20_count}个CR20标记")
        
        if cr20_count == 0:
            print("  ✗ 未找到CR20数据")
    finally:
        db.close()

def test_ministry_agriculture():
    """测试农业部数据"""
    print("\n" + "=" * 80)
    print("2. 测试农业部规模场和散户出栏环比")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        nyb_data = _get_raw_table_data(db, "NYB", "2、【生猪产业数据】")
        
        if not nyb_data:
            print("  ✗ 未找到NYB数据")
            return
        
        print(f"  ✓ 找到NYB数据，共{len(nyb_data)}行")
        
        # 检查U列（规模场）和V列（散户）的数据
        scale_count = 0
        scattered_count = 0
        
        for row_idx in range(2, min(20, len(nyb_data))):  # 检查前20行数据
            row = nyb_data[row_idx]
            if len(row) > 21:
                u_val = row[20] if len(row) > 20 else None  # U列
                v_val = row[21] if len(row) > 21 else None  # V列
                
                if u_val is not None and u_val != "":
                    try:
                        float(u_val)
                        scale_count += 1
                    except:
                        pass
                
                if v_val is not None and v_val != "":
                    try:
                        float(v_val)
                        scattered_count += 1
                    except:
                        pass
        
        print(f"  ✓ U列（规模场）有{scale_count}个有效数据")
        print(f"  ✓ V列（散户）有{scattered_count}个有效数据")
        
        if scale_count == 0 and scattered_count == 0:
            print("  ✗ 未找到有效数据")
    finally:
        db.close()

def test_slaughter():
    """测试定点屠宰数据"""
    print("\n" + "=" * 80)
    print("3. 测试定点企业屠宰环比")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        a1_data = _get_raw_table_data(db, "A1供给预测", "2、【生猪产业数据】")
        
        if not a1_data:
            print("  ✗ 未找到A1供给预测数据")
            return
        
        print(f"  ✓ 找到A1供给预测数据，共{len(a1_data)}行")
        
        # 检查AH列（索引33）的数据
        slaughter_count = 0
        
        for row_idx in range(2, min(50, len(a1_data))):  # 检查前50行数据
            row = a1_data[row_idx]
            if len(row) > 33:
                ah_val = row[33] if len(row) > 33 else None  # AH列
                
                if ah_val is not None and ah_val != "":
                    try:
                        float(ah_val)
                        slaughter_count += 1
                        if slaughter_count <= 5:  # 显示前5个数据
                            date_val = row[1] if len(row) > 1 else None
                            print(f"    行{row_idx+1}: 日期={date_val}, AH列={ah_val}")
                    except:
                        pass
        
        print(f"  ✓ AH列（定点屠宰环比）有{slaughter_count}个有效数据")
        
        if slaughter_count == 0:
            print("  ✗ 未找到有效数据")
    finally:
        db.close()

def test_api_functions():
    """测试API函数"""
    print("\n" + "=" * 80)
    print("4. 测试API函数")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 导入API函数
        from app.api.structure_analysis import (
            _get_cr20_month_on_month,
            _get_ministry_agriculture_month_on_month,
            _get_slaughter_month_on_month
        )
        
        # 测试CR20
        print("\n4.1 测试_get_cr20_month_on_month:")
        cr20_data = _get_cr20_month_on_month(db)
        print(f"  ✓ 返回{len(cr20_data)}条数据")
        if cr20_data:
            print(f"  前3条: {cr20_data[:3]}")
        
        # 测试农业部规模场
        print("\n4.2 测试_get_ministry_agriculture_month_on_month (规模场):")
        ministry_scale_data = _get_ministry_agriculture_month_on_month(db, "规模场")
        print(f"  ✓ 返回{len(ministry_scale_data)}条数据")
        if ministry_scale_data:
            print(f"  前3条: {ministry_scale_data[:3]}")
        
        # 测试农业部散户
        print("\n4.3 测试_get_ministry_agriculture_month_on_month (散户):")
        ministry_scattered_data = _get_ministry_agriculture_month_on_month(db, "散户")
        print(f"  ✓ 返回{len(ministry_scattered_data)}条数据")
        if ministry_scattered_data:
            print(f"  前3条: {ministry_scattered_data[:3]}")
        
        # 测试定点屠宰
        print("\n4.4 测试_get_slaughter_month_on_month:")
        slaughter_data = _get_slaughter_month_on_month(db)
        print(f"  ✓ 返回{len(slaughter_data)}条数据")
        if slaughter_data:
            print(f"  前3条: {slaughter_data[:3]}")
    
    finally:
        db.close()

if __name__ == "__main__":
    test_cr20()
    test_ministry_agriculture()
    test_slaughter()
    test_api_functions()
