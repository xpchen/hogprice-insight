"""
测试NYB sheet的指数计算
验证能繁母猪和新生仔猪指数的计算逻辑
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

def test_index_calculation():
    """测试指数计算"""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("测试NYB sheet指数计算")
        print("=" * 80)
        
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
        
        # 提取C列（能繁母猪环比）数据
        print("\n1. 提取C列（能繁母猪环比）数据:")
        breeding_data = []
        for row_idx, row in enumerate(table_data):
            if row_idx < 2:  # 跳过表头
                continue
            
            if len(row) > 2:
                date_val = row[1] if len(row) > 1 else None  # B列
                c_val = row[2] if len(row) > 2 else None  # C列
                
                if date_val and c_val is not None and c_val != "":
                    parsed_date = _parse_excel_date(date_val)
                    if parsed_date:
                        try:
                            value = float(c_val)
                            import math
                            if not math.isnan(value) and not math.isinf(value):
                                breeding_data.append({
                                    'date': parsed_date,
                                    'value': value
                                })
                        except:
                            pass
        
        breeding_data.sort(key=lambda x: x['date'])
        
        print(f"  找到 {len(breeding_data)} 条数据")
        print(f"  时间范围: {breeding_data[0]['date']} 至 {breeding_data[-1]['date']}")
        
        # 查找2020年1月的数据
        base_date = date(2020, 1, 1)
        print(f"\n  查找2020年1月的数据:")
        for item in breeding_data:
            if item['date'].year == 2020 and item['date'].month == 1:
                print(f"    {item['date']}: C列值={item['value']}")
                break
        
        # 计算能繁母猪指数
        print("\n2. 计算能繁母猪指数（以2020年1月为80）:")
        base_index = 80.0
        result = []
        
        for item in breeding_data:
            if item['date'] < base_date:
                continue
            
            mom = item['value']  # 环比值
            
            if len(result) == 0:
                index = base_index
            else:
                last_index = result[-1]['inventory_index']
                index = last_index * mom
            
            result.append({
                'month': item['date'].strftime('%Y-%m'),
                'inventory_index': round(index, 2),
                'mom': mom
            })
        
        print(f"  计算了 {len(result)} 个数据点")
        print(f"\n  前10个数据点:")
        for item in result[:10]:
            print(f"    {item['month']}: 指数={item['inventory_index']}, 环比={item['mom']}")
        
        print(f"\n  后10个数据点:")
        for item in result[-10:]:
            print(f"    {item['month']}: 指数={item['inventory_index']}, 环比={item['mom']}")
        
        # 提取G列（新生仔猪环比）数据
        print("\n\n3. 提取G列（新生仔猪环比）数据:")
        piglet_data = []
        for row_idx, row in enumerate(table_data):
            if row_idx < 2:  # 跳过表头
                continue
            
            if len(row) > 6:
                date_val = row[1] if len(row) > 1 else None  # B列
                g_val = row[6] if len(row) > 6 else None  # G列
                
                if date_val and g_val is not None and g_val != "":
                    parsed_date = _parse_excel_date(date_val)
                    if parsed_date:
                        try:
                            value = float(g_val)
                            import math
                            if not math.isnan(value) and not math.isinf(value):
                                piglet_data.append({
                                    'date': parsed_date,
                                    'value': value
                                })
                        except:
                            pass
        
        piglet_data.sort(key=lambda x: x['date'])
        
        print(f"  找到 {len(piglet_data)} 条数据")
        print(f"  时间范围: {piglet_data[0]['date']} 至 {piglet_data[-1]['date']}")
        
        # 查找2020年1月的数据
        print(f"\n  查找2020年1月的数据:")
        for item in piglet_data:
            if item['date'].year == 2020 and item['date'].month == 1:
                print(f"    {item['date']}: G列值={item['value']}")
                break
        
        # 计算新生仔猪指数
        print("\n4. 计算新生仔猪指数（以2020年1月为80）:")
        base_index = 80.0
        result2 = []
        
        for item in piglet_data:
            if item['date'] < base_date:
                continue
            
            mom = item['value']  # 环比值
            
            # 如果mom是负数，需要转换为比例
            if mom < 0:
                mom = 1 + mom  # 负数环比转换为比例
            
            if len(result2) == 0:
                index = base_index
            else:
                last_index = result2[-1]['inventory_index']
                index = last_index * mom
            
            result2.append({
                'month': item['date'].strftime('%Y-%m'),
                'inventory_index': round(index, 2),
                'mom': item['value'],  # 原始值
                'mom_converted': mom  # 转换后的值
            })
        
        print(f"  计算了 {len(result2)} 个数据点")
        print(f"\n  前10个数据点:")
        for item in result2[:10]:
            print(f"    {item['month']}: 指数={item['inventory_index']}, 环比={item['mom']}, 转换后={item['mom_converted']}")
        
        print(f"\n  后10个数据点:")
        for item in result2[-10:]:
            print(f"    {item['month']}: 指数={item['inventory_index']}, 环比={item['mom']}, 转换后={item['mom_converted']}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_index_calculation()
