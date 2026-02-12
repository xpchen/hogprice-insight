"""
测试统计局数据汇总API的数据解析
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
from datetime import date, datetime, timedelta

def _get_raw_table_data(db: Session, sheet_name: str):
    """获取raw_table数据"""
    sheet = db.query(RawSheet).filter(
        RawSheet.sheet_name == sheet_name
    ).first()
    
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

def _parse_excel_date(excel_date):
    """解析Excel日期"""
    if isinstance(excel_date, (int, float)):
        try:
            excel_epoch = datetime(1899, 12, 30)
            return (excel_epoch + timedelta(days=int(excel_date))).date()
        except:
            pass
    elif isinstance(excel_date, str):
        try:
            if 'T' in excel_date:
                return datetime.fromisoformat(excel_date.replace('Z', '+00:00')).date()
            return datetime.strptime(excel_date, '%Y-%m-%d').date()
        except:
            pass
    elif isinstance(excel_date, date):
        return excel_date
    elif isinstance(excel_date, datetime):
        return excel_date.date()
    return None

def test_quarterly_data():
    """测试季度数据解析"""
    db: Session = SessionLocal()
    try:
        table_data = _get_raw_table_data(db, "03.统计局季度数据")
        
        if not table_data or len(table_data) < 3:
            print("✗ 数据不存在或数据行数不足")
            return
        
        print("=" * 80)
        print("测试统计局季度数据解析")
        print("=" * 80)
        
        # 合并表头
        main_header_row = table_data[0]
        sub_header_row = table_data[1]
        
        headers = []
        for col_idx in range(1, 25):
            col_letter = chr(65 + col_idx)
            
            main_header = ""
            if col_idx < len(main_header_row) and main_header_row[col_idx]:
                main_header = str(main_header_row[col_idx]).strip()
            
            sub_header = ""
            if col_idx < len(sub_header_row) and sub_header_row[col_idx]:
                sub_header = str(sub_header_row[col_idx]).strip()
            
            if main_header and sub_header:
                header_name = f"{main_header}-{sub_header}"
            elif main_header:
                header_name = main_header
            elif sub_header:
                header_name = sub_header
            else:
                header_name = col_letter
            
            headers.append(header_name)
        
        print(f"\n表头（B-Y列）:")
        for idx, header in enumerate(headers, 1):
            col_letter = chr(65 + idx)
            print(f"  {col_letter}列: {header}")
        
        # 解析数据行
        data_rows = []
        for row_idx, row in enumerate(table_data[2:], start=3):
            if len(row) < 2:
                continue
            
            period_str = row[1] if len(row) > 1 and row[1] else None
            if not period_str:
                continue
            
            parsed_date = _parse_excel_date(period_str)
            if parsed_date:
                year = parsed_date.year
                quarter = (parsed_date.month - 1) // 3 + 1
                period = f"{year}Q{quarter}"
            else:
                period = str(period_str)
            
            # 提取J列（出栏量）和P列（屠宰量）
            output_val = row[9] if len(row) > 9 else None
            slaughter_val = row[15] if len(row) > 15 else None
            
            output_volume = None
            if output_val is not None and output_val != "":
                try:
                    output_volume = float(output_val)
                    import math
                    if math.isnan(output_volume) or math.isinf(output_volume):
                        output_volume = None
                except:
                    pass
            
            slaughter_volume = None
            if slaughter_val is not None and slaughter_val != "":
                try:
                    slaughter_volume = float(slaughter_val)
                    import math
                    if math.isnan(slaughter_volume) or math.isinf(slaughter_volume):
                        slaughter_volume = None
                except:
                    pass
            
            if output_volume is not None or slaughter_volume is not None:
                data_rows.append({
                    'period': period,
                    'output_volume': output_volume,
                    'slaughter_volume': slaughter_volume
                })
        
        print(f"\n解析结果:")
        print(f"  总数据点数: {len(data_rows)}")
        print(f"\n前10个数据点:")
        for item in data_rows[:10]:
            print(f"  {item['period']}: 出栏量={item['output_volume']}, 屠宰量={item['slaughter_volume']}")
        
        print(f"\n后10个数据点:")
        for item in data_rows[-10:]:
            print(f"  {item['period']}: 出栏量={item['output_volume']}, 屠宰量={item['slaughter_volume']}")
        
        latest_period = data_rows[-1]['period'] if data_rows else None
        print(f"\n最新季度: {latest_period}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_quarterly_data()
