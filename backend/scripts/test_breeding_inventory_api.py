"""
测试能繁母猪存栏&猪价API
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
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from sqlalchemy import func, or_

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

def test_api():
    """测试API逻辑"""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("测试能繁母猪存栏&猪价API")
        print("=" * 80)
        
        # 1. 获取NYB数据
        print("\n1. 获取NYB数据:")
        nyb_data = _get_raw_table_data(db, "NYB")
        
        if not nyb_data:
            print("  ✗ 未找到NYB数据")
            return
        
        print(f"  ✓ 找到NYB数据，共{len(nyb_data)}行")
        
        # 2. 提取C列数据
        print("\n2. 提取C列（能繁母猪环比）数据:")
        inventory_data = []
        for row_idx, row in enumerate(nyb_data):
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
                                inventory_data.append({
                                    'date': parsed_date,
                                    'value': value
                                })
                        except:
                            pass
        
        print(f"  ✓ 提取了{len(inventory_data)}条数据")
        
        if len(inventory_data) == 0:
            print("  ✗ 没有有效数据")
            return
        
        # 3. 计算指数
        print("\n3. 计算存栏指数:")
        base_date = date(2020, 1, 1)
        inventory_data.sort(key=lambda x: x['date'])
        
        result = []
        base_index = 80.0
        
        for item in inventory_data:
            if item['date'] < base_date:
                continue
            
            mom = item['value']
            
            if mom <= 0:
                continue
            
            if len(result) == 0:
                index = base_index
            else:
                last_index = result[-1]['inventory_index']
                index = last_index * mom
            
            result.append({
                'month': item['date'].strftime('%Y-%m'),
                'inventory_index': round(index, 2),
                'inventory_month': item['date'].strftime('%Y-%m'),
                'mom': mom
            })
        
        print(f"  ✓ 计算了{len(result)}个数据点")
        
        if len(result) == 0:
            print("  ✗ 没有计算结果")
            return
        
        print(f"\n  前10个数据点:")
        for item in result[:10]:
            print(f"    {item['month']}: 指数={item['inventory_index']}, 环比={item['mom']}")
        
        print(f"\n  后10个数据点:")
        for item in result[-10:]:
            print(f"    {item['month']}: 指数={item['inventory_index']}, 环比={item['mom']}")
        
        # 4. 获取猪价数据
        print("\n4. 获取猪价数据:")
        # 优先查找：分省区猪价sheet中的"中国"列
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价",
            or_(
                DimMetric.raw_header.like('%中国%'),
                DimMetric.raw_header.like('%全国%')
            )
        ).first()
        
        if not price_metric:
            price_metric = db.query(DimMetric).filter(
                DimMetric.sheet_name.like('%钢联%'),
                or_(
                    DimMetric.raw_header.like('%全国%价%'),
                    DimMetric.raw_header.like('%中国%价%')
                )
            ).first()
        
        if not price_metric:
            print("  ✗ 未找到猪价指标")
            return
        
        print(f"  ✓ 找到猪价指标: {price_metric.metric_name}")
        
        # 查询价格数据并按月聚合
        price_monthly = db.query(
            func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
            func.avg(FactObservation.value).label('monthly_avg')
        ).filter(
            FactObservation.metric_id == price_metric.id,
            FactObservation.period_type == 'day'
        ).group_by('month').order_by('month').all()
        
        # price_dict的key格式可能是"YYYY-MM-01"或"YYYY-MM"，需要统一处理
        price_dict = {}
        for item in price_monthly:
            if item.monthly_avg:
                month_key = item.month
                # 如果格式是"YYYY-MM-01"，提取"YYYY-MM"
                if month_key and len(month_key) > 7:
                    month_key = month_key[:7]  # 取前7个字符"YYYY-MM"
                price_dict[month_key] = float(item.monthly_avg)
        
        print(f"  ✓ 找到{len(price_dict)}个月的价格数据")
        
        # 显示价格数据的时间范围
        if price_dict:
            price_months = sorted(price_dict.keys())
            print(f"  价格数据时间范围: {price_months[0]} 至 {price_months[-1]}")
            print(f"  前5个月: {price_months[:5]}")
            print(f"  后5个月: {price_months[-5:]}")
        
        # 5. 合并数据（滞后10个月）
        print("\n5. 合并数据（滞后10个月）:")
        final_result = []
        for item in result:
            inventory_month = item['inventory_month']
            inventory_date = datetime.strptime(inventory_month + '-01', '%Y-%m-%d').date()
            price_date = inventory_date + timedelta(days=300)  # 约10个月
            price_month = price_date.strftime('%Y-%m')
            
            price = price_dict.get(price_month)
            
            final_result.append({
                'month': inventory_month,
                'inventory_index': item['inventory_index'],
                'price': round(price, 2) if price else None,
                'price_month': price_month
            })
        
        print(f"  ✓ 合并了{len(final_result)}个数据点")
        
        # 显示前10个数据点的滞后计算情况
        print(f"\n  前10个数据点的滞后计算:")
        for item in final_result[:10]:
            print(f"    {item['month']}: 指数={item['inventory_index']}, 价格月份={item['price_month']}, 价格={item['price']}")
        
        # 统计有价格数据的点
        with_price = [item for item in final_result if item['price'] is not None]
        print(f"  ✓ 其中{len(with_price)}个数据点有价格数据")
        
        if len(with_price) > 0:
            print(f"\n  前10个有价格的数据点:")
            for item in with_price[:10]:
                print(f"    {item['month']}: 指数={item['inventory_index']}, 价格={item['price']}, 价格月份={item['price_month']}")
        
        latest_month = final_result[-1]['month'] if final_result else None
        print(f"\n  最新月份: {latest_month}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_api()
