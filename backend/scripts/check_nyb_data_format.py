"""
检查NYB sheet中C列和G列的数据格式
确认环比值的含义
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import json
from datetime import date, datetime, timedelta

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable

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

def check_data_format():
    """检查数据格式"""
    db: Session = SessionLocal()
    try:
        sheet = db.query(RawSheet).filter(
            RawSheet.sheet_name == "NYB"
        ).first()
        
        if not sheet:
            print("✗ 未找到'NYB'sheet")
            return
        
        raw_table = db.query(RawTable).filter(
            RawTable.raw_sheet_id == sheet.id
        ).first()
        
        if not raw_table:
            print("✗ 没有数据表")
            return
        
        table_data = raw_table.table_json
        if isinstance(table_data, str):
            table_data = json.loads(table_data)
        
        print("=" * 80)
        print("检查NYB sheet数据格式")
        print("=" * 80)
        
        # 提取2020年的数据（重点关注前几个月）
        print("\n2020年前6个月的数据（C列能繁环比，G列新生仔猪环比）:")
        breeding_data = []
        piglet_data = []
        
        for row_idx, row in enumerate(table_data):
            if row_idx < 2:  # 跳过表头
                continue
            
            if len(row) > 6:
                date_val = row[1] if len(row) > 1 else None  # B列
                c_val = row[2] if len(row) > 2 else None  # C列
                g_val = row[6] if len(row) > 6 else None  # G列
                
                if date_val:
                    parsed_date = _parse_excel_date(date_val)
                    if parsed_date and parsed_date.year == 2020 and parsed_date.month <= 6:
                        print(f"  {parsed_date.strftime('%Y-%m')}: C列={c_val}, G列={g_val}")
                        
                        if c_val is not None and c_val != "":
                            try:
                                breeding_data.append({
                                    'date': parsed_date,
                                    'value': float(c_val)
                                })
                            except:
                                pass
                        
                        if g_val is not None and g_val != "":
                            try:
                                piglet_data.append({
                                    'date': parsed_date,
                                    'value': float(g_val)
                                })
                            except:
                                pass
        
        # 分析能繁母猪数据
        print("\n\n能繁母猪环比数据分析:")
        if breeding_data:
            print("  数据值:")
            for item in breeding_data:
                print(f"    {item['date'].strftime('%Y-%m')}: {item['value']}")
            
            # 尝试理解数据含义
            print("\n  数据含义分析:")
            print("    如果这些值是环比比例（本月/上月）:")
            base = 80.0
            for item in breeding_data:
                if item['date'].month == 1:
                    index = base
                else:
                    prev_item = breeding_data[breeding_data.index(item) - 1]
                    index = prev_item.get('index', base) * item['value']
                    item['index'] = index
                print(f"      {item['date'].strftime('%Y-%m')}: 指数={index:.2f}, 环比={item['value']}")
        
        # 分析新生仔猪数据
        print("\n\n新生仔猪环比数据分析:")
        if piglet_data:
            print("  数据值:")
            for item in piglet_data:
                print(f"    {item['date'].strftime('%Y-%m')}: {item['value']}")
            
            # 尝试理解数据含义
            print("\n  数据含义分析:")
            print("    如果这些值是环比比例（本月/上月），负数需要转换:")
            base = 80.0
            for item in piglet_data:
                mom = item['value']
                if mom < 0:
                    mom_converted = 1 + mom
                else:
                    mom_converted = mom
                
                if item['date'].month == 1:
                    index = base
                else:
                    prev_item = piglet_data[piglet_data.index(item) - 1]
                    index = prev_item.get('index', base) * mom_converted
                    item['index'] = index
                print(f"      {item['date'].strftime('%Y-%m')}: 指数={index:.2f}, 环比={mom}, 转换后={mom_converted}")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_data_format()
