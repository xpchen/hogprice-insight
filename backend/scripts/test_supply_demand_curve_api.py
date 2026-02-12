"""
测试供需曲线API的数据解析
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
from datetime import date, datetime

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
            from datetime import timedelta
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

def test_parsing():
    """测试数据解析"""
    db: Session = SessionLocal()
    try:
        curve_data = _get_raw_table_data(db, "供需曲线")
        
        if not curve_data or len(curve_data) <= 30:
            print("✗ 数据不存在或数据行数不足")
            return
        
        print("=" * 80)
        print("测试供需曲线数据解析")
        print("=" * 80)
        
        data_dict = {}
        
        # 遍历第31行到第50行
        for row_idx in range(30, min(51, len(curve_data))):
            row = curve_data[row_idx]
            if not row or len(row) < 3:
                continue
            
            # 每3列为一组：日期、屠宰系数、价格系数
            for start_col in range(1, min(len(row), 30), 3):
                if start_col + 2 < len(row):
                    date_val = row[start_col]
                    slaughter_val = row[start_col + 1]
                    price_val = row[start_col + 2]
                    
                    if not date_val:
                        continue
                    
                    # 解析日期
                    parsed_date = _parse_excel_date(date_val)
                    if not parsed_date:
                        continue
                    
                    month_str = parsed_date.strftime('%Y-%m')
                    
                    # 解析屠宰系数
                    slaughter_coef = None
                    if slaughter_val is not None and slaughter_val != "":
                        try:
                            slaughter_coef = float(slaughter_val)
                            import math
                            if math.isnan(slaughter_coef) or math.isinf(slaughter_coef):
                                slaughter_coef = None
                        except (ValueError, TypeError):
                            pass
                    
                    # 解析价格系数
                    price_coef = None
                    if price_val is not None and price_val != "":
                        try:
                            price_coef = float(price_val)
                            import math
                            if math.isnan(price_coef) or math.isinf(price_coef):
                                price_coef = None
                        except (ValueError, TypeError):
                            pass
                    
                    # 如果有有效数据，添加到结果中
                    if slaughter_coef is not None or price_coef is not None:
                        if month_str in data_dict:
                            existing = data_dict[month_str]
                            if slaughter_coef is not None:
                                existing['slaughter_coefficient'] = round(slaughter_coef, 4)
                            if price_coef is not None:
                                existing['price_coefficient'] = round(price_coef, 4)
                        else:
                            data_dict[month_str] = {
                                'month': month_str,
                                'slaughter_coefficient': round(slaughter_coef, 4) if slaughter_coef is not None else None,
                                'price_coefficient': round(price_coef, 4) if price_coef is not None else None
                            }
        
        # 转换为列表并排序
        result = [
            data_dict[key]
            for key in sorted(data_dict.keys())
        ]
        
        print(f"\n解析结果:")
        print(f"  总数据点数: {len(result)}")
        print(f"\n前10个数据点:")
        for item in result[:10]:
            print(f"  {item['month']}: 屠宰系数={item['slaughter_coefficient']}, 价格系数={item['price_coefficient']}")
        
        print(f"\n后10个数据点:")
        for item in result[-10:]:
            print(f"  {item['month']}: 屠宰系数={item['slaughter_coefficient']}, 价格系数={item['price_coefficient']}")
        
        latest_month = result[-1]['month'] if result else None
        print(f"\n最新月份: {latest_month}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_parsing()
