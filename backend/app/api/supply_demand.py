"""
E3. 供需曲线 API
包含3个图表：
1. 长周期生猪供需曲线（定点屠宰系数、猪价系数）
2. 能繁母猪存栏&猪价（滞后10个月）
3. 新生仔猪&猪价（滞后10个月）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.dialects.mysql import json as mysql_json
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import json
import math

from app.core.database import get_db
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

router = APIRouter(prefix="/api/v1/supply-demand", tags=["supply-demand"])


class SupplyDemandCurvePoint(BaseModel):
    """供需曲线数据点"""
    month: str  # 月份 YYYY-MM
    slaughter_coefficient: Optional[float] = None  # 定点屠宰系数（当月/平均值）
    price_coefficient: Optional[float] = None  # 猪价系数（月度均值/历年平均值）


class SupplyDemandCurveResponse(BaseModel):
    """供需曲线响应"""
    data: List[SupplyDemandCurvePoint]
    latest_month: Optional[str] = None


class InventoryPricePoint(BaseModel):
    """存栏价格数据点"""
    month: str  # 月份 YYYY-MM
    inventory_index: Optional[float] = None  # 存栏指数（以2020年1月为80）
    price: Optional[float] = None  # 猪价
    inventory_month: Optional[str] = None  # 存栏月份（用于滞后计算）


class InventoryPriceResponse(BaseModel):
    """存栏价格响应"""
    data: List[InventoryPricePoint]
    latest_month: Optional[str] = None


def _get_raw_table_data(db: Session, sheet_name: str) -> Optional[List[List]]:
    """获取raw_table数据"""
    sheet = db.query(RawSheet).join(RawFile).filter(
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


def _parse_excel_date(excel_date: any) -> Optional[date]:
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


@router.get("/curve", response_model=SupplyDemandCurveResponse)
async def get_supply_demand_curve(
    db: Session = Depends(get_db)
):
    """
    获取长周期生猪供需曲线数据
    定点屠宰系数 = 当月/平均值
    猪价系数 = 月度均值/历年平均值
    """
    # 1. 获取定点屠宰数据（日度，需要按月聚合）
    slaughter_metric = db.query(DimMetric).filter(
        or_(
            DimMetric.raw_header.like('%日度屠宰量%'),
            DimMetric.raw_header.like('%日屠宰量%'),
            DimMetric.raw_header.like('%屠宰量合计%')
        ),
        DimMetric.freq.in_(["D", "daily"])
    ).first()
    
    # 2. 获取钢联全国猪价数据（日度，需要按月聚合）
    # 优先查找：分省区猪价sheet中的"中国"列
    price_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "分省区猪价",
        or_(
            DimMetric.raw_header.like('%中国%'),
            DimMetric.raw_header.like('%全国%')
        ),
        DimMetric.freq.in_(["D", "daily"])
    ).first()
    
    # 如果没找到，尝试通过metric_key查找
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'GL_D_PRICE_NATION',
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    
    # 如果还没找到，尝试其他方式
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name.like('%钢联%'),
            or_(
                DimMetric.raw_header.like('%全国%价%'),
                DimMetric.raw_header.like('%中国%价%')
            ),
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    
    if not slaughter_metric or not price_metric:
        return SupplyDemandCurveResponse(
            data=[],
            latest_month=None
        )
    
    # 查询屠宰数据并按月聚合
    slaughter_monthly = db.query(
        func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
        func.avg(FactObservation.value).label('monthly_avg')
    ).filter(
        FactObservation.metric_id == slaughter_metric.id,
        FactObservation.period_type == 'day'
    ).group_by('month').order_by('month').all()
    
    # 查询价格数据并按月聚合
    price_monthly = db.query(
        func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
        func.avg(FactObservation.value).label('monthly_avg')
    ).filter(
        FactObservation.metric_id == price_metric.id,
        FactObservation.period_type == 'day'
    ).group_by('month').order_by('month').all()
    
    # 计算平均值
    slaughter_values = [float(item.monthly_avg) for item in slaughter_monthly if item.monthly_avg]
    price_values = [float(item.monthly_avg) for item in price_monthly if item.monthly_avg]
    
    slaughter_avg = sum(slaughter_values) / len(slaughter_values) if slaughter_values else None
    price_avg = sum(price_values) / len(price_values) if price_values else None
    
    # 构建数据点
    result = []
    slaughter_dict = {item.month: float(item.monthly_avg) for item in slaughter_monthly if item.monthly_avg}
    price_dict = {item.month: float(item.monthly_avg) for item in price_monthly if item.monthly_avg}
    
    all_months = sorted(set(list(slaughter_dict.keys()) + list(price_dict.keys())))
    
    for month in all_months:
        slaughter_coef = None
        price_coef = None
        
        if month in slaughter_dict and slaughter_avg and slaughter_avg > 0:
            slaughter_coef = slaughter_dict[month] / slaughter_avg
        
        if month in price_dict and price_avg and price_avg > 0:
            price_coef = price_dict[month] / price_avg
        
        if slaughter_coef is not None or price_coef is not None:
            result.append(SupplyDemandCurvePoint(
                month=month,
                slaughter_coefficient=round(slaughter_coef, 4) if slaughter_coef else None,
                price_coefficient=round(price_coef, 4) if price_coef else None
            ))
    
    latest_month = result[-1].month if result else None
    
    return SupplyDemandCurveResponse(
        data=result,
        latest_month=latest_month
    )


@router.get("/breeding-inventory-price", response_model=InventoryPriceResponse)
async def get_breeding_inventory_price(
    db: Session = Depends(get_db)
):
    """
    获取能繁母猪存栏&猪价（滞后10个月）
    能繁母猪存栏指数：以2020年1月为80，按照农业部的环比累计计算
    数据来源：NYB sheet，能繁用C列
    """
    # 1. 获取NYB数据
    nyb_data = _get_raw_table_data(db, "NYB")
    
    if not nyb_data:
        return InventoryPriceResponse(
            data=[],
            latest_month=None
        )
    
    # 2. 提取C列（能繁母猪存栏）数据
    # 假设第1行是表头，第2行开始是数据
    # C列是索引2
    inventory_data = []
    for row_idx, row in enumerate(nyb_data):
        if row_idx < 1:  # 跳过表头
            continue
        
        if len(row) > 2:
            date_val = row[0] if len(row) > 0 else None
            c_val = row[2] if len(row) > 2 else None
            
            if date_val and c_val is not None and c_val != "":
                parsed_date = _parse_excel_date(date_val)
                if parsed_date:
                    try:
                        value = float(c_val)
                        if not math.isnan(value) and not math.isinf(value):
                            inventory_data.append({
                                'date': parsed_date,
                                'value': value
                            })
                    except:
                        pass
    
    # 3. 计算存栏指数（以2020年1月为80，按照环比累计）
    # 先找到2020年1月的数据作为基准
    base_value = None
    base_date = date(2020, 1, 1)
    
    for item in inventory_data:
        if item['date'].year == 2020 and item['date'].month == 1:
            base_value = item['value']
            break
    
    if not base_value:
        return InventoryPriceResponse(
            data=[],
            latest_month=None
        )
    
    # 按日期排序
    inventory_data.sort(key=lambda x: x['date'])
    
    # 计算指数（以2020年1月为80）
    result = []
    prev_value = base_value
    
    for item in inventory_data:
        if item['date'] < base_date:
            continue
        
        current_value = item['value']
        # 计算环比
        if prev_value and prev_value > 0:
            mom = current_value / prev_value
            # 累计计算指数
            if len(result) == 0:
                index = 80.0  # 2020年1月为80
            else:
                last_index = result[-1]['inventory_index']
                index = last_index * mom
            
            result.append({
                'month': item['date'].strftime('%Y-%m'),
                'inventory_index': round(index, 2),
                'inventory_month': item['date'].strftime('%Y-%m')
            })
            
            prev_value = current_value
    
    # 4. 获取猪价数据（滞后10个月）
    price_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name.like('%钢联%'),
        or_(
            DimMetric.raw_header.like('%全国%价%'),
            DimMetric.raw_header.like('%中国%价%')
        ),
        DimMetric.freq == "D"
    ).first()
    
    if price_metric:
        # 查询价格数据并按月聚合
        price_monthly = db.query(
            func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
            func.avg(FactObservation.value).label('monthly_avg')
        ).filter(
            FactObservation.metric_id == price_metric.id,
            FactObservation.period_type == 'day'
        ).group_by('month').order_by('month').all()
        
        price_dict = {item.month: float(item.monthly_avg) for item in price_monthly if item.monthly_avg}
        
        # 合并数据（滞后10个月）
        final_result = []
        for item in result:
            inventory_month = item['inventory_month']
            # 滞后10个月
            inventory_date = datetime.strptime(inventory_month + '-01', '%Y-%m-%d').date()
            price_date = inventory_date + timedelta(days=300)  # 约10个月
            price_month = price_date.strftime('%Y-%m')
            
            price = price_dict.get(price_month)
            
            final_result.append(InventoryPricePoint(
                month=inventory_month,
                inventory_index=item['inventory_index'],
                price=round(price, 2) if price else None,
                inventory_month=inventory_month
            ))
        
        result = final_result
    
    latest_month = result[-1].month if result else None
    
    return InventoryPriceResponse(
        data=result,
        latest_month=latest_month
    )


@router.get("/piglet-price", response_model=InventoryPriceResponse)
async def get_piglet_price(
    db: Session = Depends(get_db)
):
    """
    获取新生仔猪&猪价（滞后10个月）
    新生仔猪指数：以2020年1月为80，按照农业部的环比累计计算
    数据来源：NYB sheet，新生仔猪用G列
    """
    # 1. 获取NYB数据
    nyb_data = _get_raw_table_data(db, "NYB")
    
    if not nyb_data:
        return InventoryPriceResponse(
            data=[],
            latest_month=None
        )
    
    # 2. 提取G列（新生仔猪存栏）数据
    # G列是索引6
    inventory_data = []
    for row_idx, row in enumerate(nyb_data):
        if row_idx < 1:  # 跳过表头
            continue
        
        if len(row) > 6:
            date_val = row[0] if len(row) > 0 else None
            g_val = row[6] if len(row) > 6 else None
            
            if date_val and g_val is not None and g_val != "":
                parsed_date = _parse_excel_date(date_val)
                if parsed_date:
                    try:
                        value = float(g_val)
                        if not math.isnan(value) and not math.isinf(value):
                            inventory_data.append({
                                'date': parsed_date,
                                'value': value
                            })
                    except:
                        pass
    
    # 3. 计算存栏指数（以2020年1月为80，按照环比累计）
    base_value = None
    base_date = date(2020, 1, 1)
    
    for item in inventory_data:
        if item['date'].year == 2020 and item['date'].month == 1:
            base_value = item['value']
            break
    
    if not base_value:
        return InventoryPriceResponse(
            data=[],
            latest_month=None
        )
    
    inventory_data.sort(key=lambda x: x['date'])
    
    result = []
    prev_value = base_value
    
    for item in inventory_data:
        if item['date'] < base_date:
            continue
        
        current_value = item['value']
        if prev_value and prev_value > 0:
            mom = current_value / prev_value
            if len(result) == 0:
                index = 80.0
            else:
                last_index = result[-1]['inventory_index']
                index = last_index * mom
            
            result.append({
                'month': item['date'].strftime('%Y-%m'),
                'inventory_index': round(index, 2),
                'inventory_month': item['date'].strftime('%Y-%m')
            })
            
            prev_value = current_value
    
    # 4. 获取猪价数据（滞后10个月）
    # 优先查找：分省区猪价sheet中的"中国"列
    price_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "分省区猪价",
        or_(
            DimMetric.raw_header.like('%中国%'),
            DimMetric.raw_header.like('%全国%')
        ),
        DimMetric.freq.in_(["D", "daily"])
    ).first()
    
    # 如果没找到，尝试通过metric_key查找
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'GL_D_PRICE_NATION',
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    
    # 如果还没找到，尝试其他方式
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name.like('%钢联%'),
            or_(
                DimMetric.raw_header.like('%全国%价%'),
                DimMetric.raw_header.like('%中国%价%')
            ),
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    
    if price_metric:
        price_monthly = db.query(
            func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
            func.avg(FactObservation.value).label('monthly_avg')
        ).filter(
            FactObservation.metric_id == price_metric.id,
            FactObservation.period_type == 'day'
        ).group_by('month').order_by('month').all()
        
        price_dict = {item.month: float(item.monthly_avg) for item in price_monthly if item.monthly_avg}
        
        final_result = []
        for item in result:
            inventory_month = item['inventory_month']
            inventory_date = datetime.strptime(inventory_month + '-01', '%Y-%m-%d').date()
            price_date = inventory_date + timedelta(days=300)
            price_month = price_date.strftime('%Y-%m')
            
            price = price_dict.get(price_month)
            
            final_result.append(InventoryPricePoint(
                month=inventory_month,
                inventory_index=item['inventory_index'],
                price=round(price, 2) if price else None,
                inventory_month=inventory_month
            ))
        
        result = final_result
    
    latest_month = result[-1].month if result else None
    
    return InventoryPriceResponse(
        data=result,
        latest_month=latest_month
    )
