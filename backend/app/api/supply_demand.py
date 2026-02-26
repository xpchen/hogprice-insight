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


def _get_raw_table_data(db: Session, sheet_name: str, filename_pattern: str = None) -> Optional[List[List]]:
    """获取raw_table数据"""
    query = db.query(RawSheet).join(RawFile).filter(RawSheet.sheet_name == sheet_name)
    if filename_pattern:
        query = query.filter(RawFile.filename.like(f"%{filename_pattern}%"))
    sheet = query.first()
    
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


def _extract_month_str(d: date) -> str:
    """日期转 YYYY-MM"""
    return d.strftime('%Y-%m')


def _compute_curve_from_backend(db: Session) -> Optional[SupplyDemandCurveResponse]:
    """
    后端计算供需曲线系数
    - 屠宰：A1供给预测 AG列（定点屠宰），多列头，数据从第3行起
    - 价格：钢联全国猪价（fact_observation 按月聚合）
    - 历年范围：数据库有哪些年份就用哪些年份
    """
    # 1. 屠宰：A1供给预测 AG列（索引32），多列头数据从第3行起
    a1_data = _get_raw_table_data(db, "A1供给预测", "2、【生猪产业数据】")
    if not a1_data:
        a1_data = _get_raw_table_data(db, "A1供给预测", "生猪产业数据")
    if not a1_data or len(a1_data) < 3:
        return None

    AG_IDX = 32
    DATE_COL = 1
    HEADER_ROWS = 2  # 前2行为表头

    slaughter_by_month = {}  # YYYY-MM -> value
    slaughter_years = set()
    for row_idx in range(HEADER_ROWS, len(a1_data)):
        row = a1_data[row_idx]
        if len(row) <= AG_IDX:
            continue
        date_val = row[DATE_COL] if len(row) > DATE_COL else None
        ag_val = row[AG_IDX]
        if not date_val or ag_val is None or ag_val == "":
            continue
        parsed = _parse_excel_date(date_val)
        if not parsed:
            continue
        try:
            v = float(ag_val)
            if math.isnan(v) or math.isinf(v) or v <= 0:
                continue
        except (ValueError, TypeError):
            continue
        month_str = _extract_month_str(parsed)
        slaughter_by_month[month_str] = v
        slaughter_years.add(parsed.year)

    if not slaughter_by_month:
        return None

    # 2. 价格：钢联全国猪价
    price_metric = db.query(DimMetric).filter(
        func.json_extract(DimMetric.parse_json, '$.metric_key') == 'GL_D_PRICE_NATION',
        DimMetric.freq.in_(["D", "daily"])
    ).first()
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价",
            or_(
                DimMetric.raw_header.like('%中国%'),
                DimMetric.raw_header.like('%全国%')
            ),
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name.like('%钢联%'),
            or_(
                DimMetric.raw_header.like('%全国%价%'),
                DimMetric.raw_header.like('%中国%价%')
            ),
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    if not price_metric:
        return None

    price_rows = db.query(
        func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
        func.avg(FactObservation.value).label('monthly_avg')
    ).filter(
        FactObservation.metric_id == price_metric.id,
        FactObservation.period_type == 'day'
    ).group_by('month').order_by('month').all()

    price_by_month = {}
    price_years = set()
    for r in price_rows:
        if r.monthly_avg is None:
            continue
        mk = r.month[:7] if r.month and len(r.month) > 7 else r.month
        price_by_month[mk] = float(r.monthly_avg)
        if mk:
            price_years.add(int(mk[:4]))

    if not price_by_month:
        return None

    # 3. 历年范围：取两种数据都有的年份
    common_years = slaughter_years & price_years
    if not common_years:
        common_years = slaughter_years | price_years
    if not common_years:
        return None

    # 4. 计算各月历年均值（仅用 common_years）
    slaughter_avg_by_month_num = {}  # 1-12 -> avg
    price_avg_by_month_num = {}  # 1-12 -> avg
    for m in range(1, 13):
        slaughter_vals = []
        price_vals = []
        for y in common_years:
            mm = f"{y}-{m:02d}"
            if mm in slaughter_by_month:
                slaughter_vals.append(slaughter_by_month[mm])
            if mm in price_by_month:
                price_vals.append(price_by_month[mm])
        if slaughter_vals:
            slaughter_avg_by_month_num[m] = sum(slaughter_vals) / len(slaughter_vals)
        if price_vals:
            price_avg_by_month_num[m] = sum(price_vals) / len(price_vals)

    # 5. 计算系数
    all_months = sorted(set(list(slaughter_by_month.keys()) + list(price_by_month.keys())))
    result = []
    for month_str in all_months:
        slaughter_coef = None
        price_coef = None
        parts = month_str.split('-')
        if len(parts) == 2:
            try:
                month_num = int(parts[1])
            except ValueError:
                month_num = 0
        else:
            month_num = 0

        if month_str in slaughter_by_month and month_num and month_num in slaughter_avg_by_month_num:
            avg_s = slaughter_avg_by_month_num[month_num]
            if avg_s and avg_s > 0:
                slaughter_coef = slaughter_by_month[month_str] / avg_s
        if month_str in price_by_month and month_num and month_num in price_avg_by_month_num:
            avg_p = price_avg_by_month_num[month_num]
            if avg_p and avg_p > 0:
                price_coef = price_by_month[month_str] / avg_p

        if slaughter_coef is not None or price_coef is not None:
            result.append(SupplyDemandCurvePoint(
                month=month_str,
                slaughter_coefficient=round(slaughter_coef, 4) if slaughter_coef is not None else None,
                price_coefficient=round(price_coef, 4) if price_coef is not None else None
            ))

    if not result:
        return None

    latest = result[-1].month if result else None
    return SupplyDemandCurveResponse(data=result, latest_month=latest)


@router.get("/curve", response_model=SupplyDemandCurveResponse)
async def get_supply_demand_curve(
    db: Session = Depends(get_db)
):
    """
    获取长周期生猪供需曲线数据
    优先使用后端计算：屠宰=A1供给预测AG列，价格=钢联全国猪价，历年=DB实际年份
    备选：供需曲线sheet预计算值，最后：fact_observation
    """
    # 1. 优先后端计算（A1 AG列 + 钢联价格，历年用DB实际年份）
    backend_result = _compute_curve_from_backend(db)
    if backend_result and len(backend_result.data) > 0:
        return backend_result

    # 2. 从"供需曲线"sheet读取预计算数据
    curve_data = _get_raw_table_data(db, "供需曲线")
    
    if curve_data and len(curve_data) > 30:
        # 从第31行开始解析数据（索引30）
        result = []
        data_dict = {}  # 用于去重，key为月份YYYY-MM
        
        # 遍历第31行到第50行（根据实际数据调整）
        for row_idx in range(30, min(51, len(curve_data))):
            row = curve_data[row_idx]
            if not row or len(row) < 3:
                continue
            
            # 每3列为一组：日期、屠宰系数、价格系数
            # B列(索引1): 日期, C列(索引2): 屠宰系数, D列(索引3): 价格系数
            # E列(索引4): 日期, F列(索引5): 屠宰系数, G列(索引6): 价格系数
            # 以此类推
            
            col_groups = []
            for start_col in range(1, min(len(row), 20), 3):  # 每3列一组，最多处理到第20列
                if start_col + 2 < len(row):
                    date_val = row[start_col] if start_col < len(row) else None
                    slaughter_val = row[start_col + 1] if start_col + 1 < len(row) else None
                    price_val = row[start_col + 2] if start_col + 2 < len(row) else None
                    
                    if date_val:
                        col_groups.append({
                            'date': date_val,
                            'slaughter': slaughter_val,
                            'price': price_val
                        })
            
            # 解析每组数据
            for group in col_groups:
                date_val = group['date']
                slaughter_val = group['slaughter']
                price_val = group['price']
                
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
                        if math.isnan(slaughter_coef) or math.isinf(slaughter_coef):
                            slaughter_coef = None
                    except (ValueError, TypeError):
                        pass
                
                # 解析价格系数
                price_coef = None
                if price_val is not None and price_val != "":
                    try:
                        price_coef = float(price_val)
                        if math.isnan(price_coef) or math.isinf(price_coef):
                            price_coef = None
                    except (ValueError, TypeError):
                        pass
                
                # 如果有有效数据，添加到结果中
                if slaughter_coef is not None or price_coef is not None:
                    # 如果该月份已存在，合并数据
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
            SupplyDemandCurvePoint(**data_dict[key])
            for key in sorted(data_dict.keys())
        ]
        
        latest_month = result[-1].month if result else None
        
        return SupplyDemandCurveResponse(
            data=result,
            latest_month=latest_month
        )
    
    # 如果"供需曲线"sheet不存在，回退到原来的逻辑（从fact_observation计算）
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
    
    # 2. 提取C列（能繁母猪存栏环比）数据
    # NYB sheet结构：
    # - 第1行（索引0）：主表头（C列是"能繁环比"）
    # - 第2行（索引1）：子表头（B列是"月度"，C列是"全国"）
    # - 第3行（索引2）开始：数据（B列是日期，C列是能繁环比-全国）
    # B列是索引1，C列是索引2
    inventory_data = []
    for row_idx, row in enumerate(nyb_data):
        if row_idx < 2:  # 跳过表头（第1行和第2行）
            continue
        
        if len(row) > 2:
            date_val = row[1] if len(row) > 1 else None  # B列（索引1）是日期
            c_val = row[2] if len(row) > 2 else None  # C列（索引2）是能繁环比-全国
            
            if date_val and c_val is not None and c_val != "":
                parsed_date = _parse_excel_date(date_val)
                if parsed_date:
                    try:
                        value = float(c_val)
                        if not math.isnan(value) and not math.isinf(value):
                            inventory_data.append({
                                'date': parsed_date,
                                'value': value  # 这是环比值，需要累计计算
                            })
                    except:
                        pass
    
    # 3. 计算存栏指数（以2020年1月为80，按照环比累计）
    # C列的值是环比比例（本月/上月），如1.2表示本月是上月的1.2倍
    # 需要按照环比累计计算指数
    base_date = date(2020, 1, 1)
    
    # 按日期排序
    inventory_data.sort(key=lambda x: x['date'])
    
    # 计算指数（以2020年1月为80）
    result = []
    base_index = 80.0  # 2020年1月为80
    
    for item in inventory_data:
        if item['date'] < base_date:
            continue
        
        # C列的值是环比比例（mom），直接用于累计计算
        mom = item['value']  # 环比比例（如1.2表示本月/上月=1.2）
        
        # 过滤异常值（如果mom <= 0，可能是数据错误）
        if mom <= 0:
            continue
        
        if len(result) == 0:
            # 2020年1月，指数为80
            index = base_index
        else:
            # 累计计算：当前指数 = 上月指数 * 环比比例
            last_index = result[-1]['inventory_index']
            index = last_index * mom
        
        result.append({
            'month': item['date'].strftime('%Y-%m'),
            'inventory_index': round(index, 2),
            'inventory_month': item['date'].strftime('%Y-%m')
        })
    
    # 4. 获取猪价数据（滞后10个月）
    # 优先查找：分省区猪价sheet中的"中国"列
    price_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "分省区猪价",
        or_(
            DimMetric.raw_header.like('%中国%'),
            DimMetric.raw_header.like('%全国%')
        )
    ).first()
    
    # 如果没找到，尝试通过metric_key查找
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'GL_D_PRICE_NATION'
        ).first()
    
    # 如果还没找到，尝试其他方式
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name.like('%钢联%'),
            or_(
                DimMetric.raw_header.like('%全国%价%'),
                DimMetric.raw_header.like('%中国%价%')
            )
        ).first()
    
    if not price_metric:
        # 如果没有找到猪价数据，仍然返回存栏指数数据
        latest_month = result[-1].month if result else None
        return InventoryPriceResponse(
            data=[InventoryPricePoint(
                month=item['month'],
                inventory_index=item['inventory_index'],
                price=None,
                inventory_month=item['inventory_month']
            ) for item in result],
            latest_month=latest_month
        )
    
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
    
    latest_month = final_result[-1].month if final_result else None
    
    return InventoryPriceResponse(
        data=final_result,
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
    
    # 2. 提取G列（新生仔猪存栏环比）数据
    # NYB sheet结构：
    # - 第1行（索引0）：主表头（G列是"新生仔猪环比"）
    # - 第2行（索引1）：子表头（B列是"月度"，G列是"全国"）
    # - 第3行（索引2）开始：数据（B列是日期，G列是新生仔猪环比-全国）
    # B列是索引1，G列是索引6
    inventory_data = []
    for row_idx, row in enumerate(nyb_data):
        if row_idx < 2:  # 跳过表头（第1行和第2行）
            continue
        
        if len(row) > 6:
            date_val = row[1] if len(row) > 1 else None  # B列（索引1）是日期
            g_val = row[6] if len(row) > 6 else None  # G列（索引6）是新生仔猪环比-全国
            
            if date_val and g_val is not None and g_val != "":
                parsed_date = _parse_excel_date(date_val)
                if parsed_date:
                    try:
                        value = float(g_val)
                        if not math.isnan(value) and not math.isinf(value):
                            inventory_data.append({
                                'date': parsed_date,
                                'value': value  # 这是环比值，需要累计计算
                            })
                    except:
                        pass
    
    # 3. 计算存栏指数（以2020年1月为80，按照环比累计）
    # G列的值是环比比例（本月/上月），如-0.8可能表示环比下降，需要转换为比例
    # 但根据数据格式，G列的值可能是：
    # - 正数：直接是比例（如1.2表示本月/上月=1.2）
    # - 负数：需要转换为比例（如-0.8表示本月/上月=1-0.8=0.2）
    base_date = date(2020, 1, 1)
    
    inventory_data.sort(key=lambda x: x['date'])
    
    result = []
    base_index = 80.0  # 2020年1月为80
    
    for item in inventory_data:
        if item['date'] < base_date:
            continue
        
        # G列的值是环比，需要转换为比例
        mom_raw = item['value']  # 原始环比值
        
        # 如果mom是负数，转换为比例：mom = 1 + mom（如-0.8 -> 0.2）
        # 如果mom是正数，直接使用（如1.2表示本月/上月=1.2）
        if mom_raw < 0:
            mom = 1 + mom_raw  # 负数环比转换为比例
        else:
            mom = mom_raw  # 正数直接使用
        
        # 过滤异常值（如果mom <= 0，可能是数据错误）
        if mom <= 0:
            continue
        
        if len(result) == 0:
            # 2020年1月，指数为80
            index = base_index
        else:
            # 累计计算：当前指数 = 上月指数 * 环比比例
            last_index = result[-1]['inventory_index']
            index = last_index * mom
        
        result.append({
            'month': item['date'].strftime('%Y-%m'),
            'inventory_index': round(index, 2),
            'inventory_month': item['date'].strftime('%Y-%m')
        })
    
    # 4. 获取猪价数据（滞后10个月）
    # 优先查找：分省区猪价sheet中的"中国"列
    price_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "分省区猪价",
        or_(
            DimMetric.raw_header.like('%中国%'),
            DimMetric.raw_header.like('%全国%')
        )
    ).first()
    
    # 如果没找到，尝试通过metric_key查找
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'GL_D_PRICE_NATION'
        ).first()
    
    # 如果还没找到，尝试其他方式
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name.like('%钢联%'),
            or_(
                DimMetric.raw_header.like('%全国%价%'),
                DimMetric.raw_header.like('%中国%价%')
            )
        ).first()
    
    if not price_metric:
        # 如果没有找到猪价数据，仍然返回存栏指数数据
        latest_month = result[-1].month if result else None
        return InventoryPriceResponse(
            data=[InventoryPricePoint(
                month=item['month'],
                inventory_index=item['inventory_index'],
                price=None,
                inventory_month=item['inventory_month']
            ) for item in result],
            latest_month=latest_month
        )
    
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
    
    # 合并数据（滞后10个月）
    final_result = []
    for item in result:
        inventory_month = item['inventory_month']
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
    
    latest_month = final_result[-1].month if final_result else None
    
    return InventoryPriceResponse(
        data=final_result,
        latest_month=latest_month
    )
