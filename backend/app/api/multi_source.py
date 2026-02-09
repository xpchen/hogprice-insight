"""
E2. 多渠道汇总 API
包含3个表格：
1. 淘汰母猪屠宰环比、能繁母猪存栏环比、能繁母猪饲料环比
2. 新生仔猪存栏环比、仔猪饲料环比
3. 生猪存栏环比、育肥猪饲料环比

数据来源：【生猪产业数据】.xlsx
- NYB sheet: 能繁母猪存栏环比、新生仔猪存栏环比、生猪存栏环比
- 4.1.钢联数据 sheet: 能繁母猪存栏环比、新生仔猪存栏环比、生猪存栏环比、各种饲料环比
- 4.2涌益底稿 sheet: 能繁母猪存栏环比、生猪存栏环比、饲料环比
- 02.协会猪料 sheet: 能繁母猪饲料环比、仔猪饲料环比、育肥猪饲料环比
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import json
import math
from collections import defaultdict

from app.core.database import get_db
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

router = APIRouter(prefix="/api/v1/multi-source", tags=["multi-source"])


class MultiSourceDataPoint(BaseModel):
    """多渠道数据点"""
    month: str  # 月份 YYYY-MM
    cull_slaughter_yongyi: Optional[float] = None  # 淘汰母猪屠宰环比-涌益
    cull_slaughter_ganglian: Optional[float] = None  # 淘汰母猪屠宰环比-钢联
    breeding_inventory_yongyi: Optional[float] = None  # 能繁母猪存栏环比-涌益
    breeding_inventory_ganglian_nation: Optional[float] = None  # 能繁母猪存栏环比-钢联-全国
    breeding_inventory_ganglian_scale: Optional[float] = None  # 能繁母猪存栏环比-钢联-规模场
    breeding_inventory_ganglian_small: Optional[float] = None  # 能繁母猪存栏环比-钢联-中小散户
    breeding_inventory_nyb: Optional[float] = None  # 能繁母猪存栏环比-NYB
    breeding_feed_yongyi: Optional[float] = None  # 能繁母猪饲料环比-涌益
    breeding_feed_ganglian: Optional[float] = None  # 能繁母猪饲料环比-钢联
    breeding_feed_association: Optional[float] = None  # 能繁母猪饲料环比-协会
    piglet_inventory_yongyi: Optional[float] = None  # 新生仔猪存栏环比-涌益
    piglet_inventory_ganglian_nation: Optional[float] = None  # 新生仔猪存栏环比-钢联-全国
    piglet_inventory_ganglian_scale: Optional[float] = None  # 新生仔猪存栏环比-钢联-规模场
    piglet_inventory_ganglian_small: Optional[float] = None  # 新生仔猪存栏环比-钢联-中小散户
    piglet_inventory_nyb: Optional[float] = None  # 新生仔猪存栏环比-NYB
    piglet_feed_yongyi: Optional[float] = None  # 仔猪饲料环比-涌益
    piglet_feed_ganglian: Optional[float] = None  # 仔猪饲料环比-钢联
    piglet_feed_association: Optional[float] = None  # 仔猪饲料环比-协会
    hog_inventory_yongyi: Optional[float] = None  # 生猪存栏环比-涌益
    hog_inventory_ganglian_nation: Optional[float] = None  # 生猪存栏环比-钢联-全国
    hog_inventory_ganglian_scale: Optional[float] = None  # 生猪存栏环比-钢联-规模场
    hog_inventory_ganglian_small: Optional[float] = None  # 生猪存栏环比-钢联-中小散户
    hog_inventory_nyb: Optional[float] = None  # 生猪存栏环比-NYB
    hog_inventory_nyb_5month: Optional[float] = None  # 生猪存栏环比-NYB-5月龄
    hog_feed_yongyi: Optional[float] = None  # 育肥猪饲料环比-涌益
    hog_feed_ganglian: Optional[float] = None  # 育肥猪饲料环比-钢联
    hog_feed_association: Optional[float] = None  # 育肥猪饲料环比-协会


class MultiSourceResponse(BaseModel):
    """多渠道汇总响应"""
    data: List[MultiSourceDataPoint]
    latest_month: Optional[str] = None


def _parse_excel_date(excel_date: any) -> Optional[date]:
    """解析Excel日期（序列号或字符串）"""
    if isinstance(excel_date, (int, float)):
        # Excel日期序列号（从1900-01-01开始）
        try:
            excel_epoch = datetime(1899, 12, 30)
            return (excel_epoch + timedelta(days=int(excel_date))).date()
        except:
            pass
    elif isinstance(excel_date, str):
        try:
            if 'T' in excel_date:
                dt = datetime.fromisoformat(excel_date.replace('Z', '+00:00'))
                return dt.date()
            return datetime.strptime(excel_date, '%Y-%m-%d').date()
        except:
            pass
    elif isinstance(excel_date, date):
        return excel_date
    elif isinstance(excel_date, datetime):
        return excel_date.date()
    return None


def _get_raw_table_data(db: Session, sheet_name: str, filename: str = None) -> Optional[List[List]]:
    """获取raw_table数据"""
    query = db.query(RawSheet).join(RawFile)
    
    if filename:
        query = query.filter(RawFile.filename == filename)
    
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


def _safe_float(value: any) -> Optional[float]:
    """安全转换为float"""
    if value is None or value == "":
        return None
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except:
        return None


def _extract_nyb_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取NYB数据
    Sheet结构：
    - 第2行是表头：B列是"月度"，C列是"全国"（能繁环比），G列是"全国"（新生仔猪环比），Q列是"全国"（存栏环比），K列是"全国环比"（5月龄及以上大猪环比）
    - 数据从第3行开始（索引2）
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "NYB", "2、【生猪产业数据】.xlsx")
    
    if not table_data or len(table_data) < 3:
        return data
    
    # 数据从第3行开始（索引2），B列是日期（索引1），C列是能繁环比-全国（索引2），G列是新生仔猪环比-全国（索引6），Q列是存栏环比（索引16），K列是5月龄及以上大猪环比（索引10）
    for row in table_data[2:]:  # 跳过表头
        if len(row) < 17:
            continue
        
        date_val = _parse_excel_date(row[1])  # B列
        if not date_val:
            continue
        
        month_key = date_val.strftime("%Y-%m")
        
        # C列：能繁环比-全国（索引2）
        breeding_val = _safe_float(row[2])
        if breeding_val is not None:
            data[month_key]['breeding_inventory_nyb'] = breeding_val
        
        # G列：新生仔猪环比-全国（索引6）
        piglet_val = _safe_float(row[6])
        if piglet_val is not None:
            data[month_key]['piglet_inventory_nyb'] = piglet_val
        
        # Q列：存栏环比（索引16）
        hog_val = _safe_float(row[16])
        if hog_val is not None:
            data[month_key]['hog_inventory_nyb'] = hog_val
        
        # K列：5月龄及以上大猪环比（索引10）
        if len(row) > 10:
            hog_5month_val = _safe_float(row[10])
            if hog_5month_val is not None:
                data[month_key]['hog_inventory_nyb_5month'] = hog_5month_val
    
    return data


def _extract_association_feed_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取协会猪料数据
    Sheet结构：
    - 第1行是表头：B列是"日期"，H列是"母猪料"，M列是"仔猪料"，R列是"育肥料"
    - 第2行是子表头：I列是"环比"（母猪料），N列是"环比"（仔猪料），S列是"环比"（育肥料）
    - 数据从第3行开始（索引2）
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "02.协会猪料", "2、【生猪产业数据】.xlsx")
    
    if not table_data or len(table_data) < 3:
        return data
    
    # 数据从第3行开始（索引2），B列是日期（索引1），I列是母猪料环比（索引8），N列是仔猪料环比（索引13），S列是育肥料环比（索引18）
    for row in table_data[2:]:  # 跳过表头
        if len(row) < 19:
            continue
        
        date_val = _parse_excel_date(row[1])  # B列
        if not date_val:
            continue
        
        month_key = date_val.strftime("%Y-%m")
        
        # I列：母猪料环比（索引8）
        breeding_feed_val = _safe_float(row[8])
        if breeding_feed_val is not None:
            data[month_key]['breeding_feed_association'] = breeding_feed_val
        
        # N列：仔猪料环比（索引13）
        piglet_feed_val = _safe_float(row[13])
        if piglet_feed_val is not None:
            data[month_key]['piglet_feed_association'] = piglet_feed_val
        
        # S列：育肥料环比（索引18）
        hog_feed_val = _safe_float(row[18])
        if hog_feed_val is not None:
            data[month_key]['hog_feed_association'] = hog_feed_val
    
    return data


def _extract_yongyi_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取涌益数据（从4.2涌益底稿sheet）
    Sheet结构：
    - 第1行是表头：G列是"能繁母猪-2020年2月*"（全国），B列是"大猪存栏-2020年5月*"（全国），P列是"饲料销量环比"（猪料销量）
    - 第2行是子表头：G列是"全国"（能繁母猪），B列是"全国"（大猪存栏），P列是"猪料销量"
    - 数据从第3行开始（索引2）
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "4.2涌益底稿", "2、【生猪产业数据】.xlsx")
    
    if not table_data or len(table_data) < 3:
        return data
    
    # 数据从第3行开始（索引2），A列是日期（索引0），G列是能繁母猪环比-全国（索引6），B列是大猪存栏环比-全国（索引1），P列是猪料销量环比（索引15）
    for row in table_data[2:]:  # 跳过表头
        if len(row) < 16:
            continue
        
        date_val = _parse_excel_date(row[0])  # A列
        if not date_val:
            continue
        
        month_key = date_val.strftime("%Y-%m")
        
        # G列：能繁母猪环比-全国（索引6）
        breeding_val = _safe_float(row[6])
        if breeding_val is not None:
            data[month_key]['breeding_inventory_yongyi'] = breeding_val
        
        # B列：大猪存栏环比-全国（索引1）
        hog_val = _safe_float(row[1])
        if hog_val is not None:
            data[month_key]['hog_inventory_yongyi'] = hog_val
        
        # P列：猪料销量环比（索引15）- 这个可能是育肥猪饲料环比
        feed_val = _safe_float(row[15])
        if feed_val is not None:
            data[month_key]['hog_feed_yongyi'] = feed_val
    
    return data


def _extract_ganglian_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取钢联数据
    Sheet结构：
    - 第1行是表头：A列是"日期"，B列是"存栏环比：中小散户"（中国），L列是"能繁存栏环比"（中国），O列是"新生仔猪数环比：中小散户"（中国），S列是"育肥料环比"，W列是"仔猪饲料环比"，AA列是"母猪料环比"
    - 第2行是子表头：B列是"中国"（存栏环比），L列是"中国"（能繁存栏环比），O列是"中国"（新生仔猪数环比）
    - 数据从第4行开始（索引3），因为第3行是空的
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "4.1.钢联数据", "2、【生猪产业数据】.xlsx")
    
    if not table_data or len(table_data) < 4:
        return data
    
    # 数据从第4行开始（索引3），A列是日期（索引0），B列是存栏环比-中国（索引1），L列是能繁存栏环比-中国（索引11），O列是新生仔猪数环比-中国（索引14），S列是育肥料环比（索引18），W列是仔猪饲料环比（索引22），AA列是母猪料环比（索引26）
    for row in table_data[3:]:  # 跳过表头和第3行空行
        if len(row) < 27:
            continue
        
        date_val = _parse_excel_date(row[0])  # A列
        if not date_val:
            continue
        
        month_key = date_val.strftime("%Y-%m")
        
        # B列：存栏环比-中国（全国）
        hog_nation_val = _safe_float(row[1])
        if hog_nation_val is not None:
            data[month_key]['hog_inventory_ganglian_nation'] = hog_nation_val
        
        # L列：能繁存栏环比-中国（全国）
        breeding_val = _safe_float(row[11])
        if breeding_val is not None:
            data[month_key]['breeding_inventory_ganglian_nation'] = breeding_val
        
        # O列：新生仔猪数环比-中国（全国）
        piglet_val = _safe_float(row[14])
        if piglet_val is not None:
            data[month_key]['piglet_inventory_ganglian_nation'] = piglet_val
        
        # S列：育肥料环比
        hog_feed_val = _safe_float(row[18])
        if hog_feed_val is not None:
            data[month_key]['hog_feed_ganglian'] = hog_feed_val
        
        # W列：仔猪饲料环比
        piglet_feed_val = _safe_float(row[22])
        if piglet_feed_val is not None:
            data[month_key]['piglet_feed_ganglian'] = piglet_feed_val
        
        # AA列：母猪料环比
        breeding_feed_val = _safe_float(row[26])
        if breeding_feed_val is not None:
            data[month_key]['breeding_feed_ganglian'] = breeding_feed_val
    
    return data


def _extract_cull_slaughter_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取淘汰母猪屠宰数据
    目前没有找到对应的数据源，暂时返回空数据
    """
    return {}


@router.get("/data", response_model=MultiSourceResponse)
async def get_multi_source_data(
    months: int = Query(999, description="显示最近N个月的数据，999表示全部"),
    db: Session = Depends(get_db)
):
    """
    获取多渠道汇总数据
    数据来源：【生猪产业数据】.xlsx
    """
    # 提取各数据源的数据
    nyb_data = _extract_nyb_data(db)
    association_data = _extract_association_feed_data(db)
    yongyi_data = _extract_yongyi_data(db)
    ganglian_data = _extract_ganglian_data(db)
    cull_slaughter_data = _extract_cull_slaughter_data(db)
    
    # 合并所有月份
    all_months = set()
    all_months.update(nyb_data.keys())
    all_months.update(association_data.keys())
    all_months.update(yongyi_data.keys())
    all_months.update(ganglian_data.keys())
    all_months.update(cull_slaughter_data.keys())
    
    # 按月份排序
    sorted_months = sorted(all_months)
    
    # 如果指定了月份数，只取最近的N个月
    if months < 999:
        sorted_months = sorted_months[-months:]
    
    # 构建数据点
    data_points = []
    for month in sorted_months:
        point = MultiSourceDataPoint(month=month)
        
        # 合并各数据源
        if month in nyb_data:
            point.breeding_inventory_nyb = nyb_data[month].get('breeding_inventory_nyb')
            point.piglet_inventory_nyb = nyb_data[month].get('piglet_inventory_nyb')
            point.hog_inventory_nyb = nyb_data[month].get('hog_inventory_nyb')
            point.hog_inventory_nyb_5month = nyb_data[month].get('hog_inventory_nyb_5month')
        
        if month in association_data:
            point.breeding_feed_association = association_data[month].get('breeding_feed_association')
            point.piglet_feed_association = association_data[month].get('piglet_feed_association')
            point.hog_feed_association = association_data[month].get('hog_feed_association')
        
        if month in yongyi_data:
            point.breeding_inventory_yongyi = yongyi_data[month].get('breeding_inventory_yongyi')
            point.hog_inventory_yongyi = yongyi_data[month].get('hog_inventory_yongyi')
            point.hog_feed_yongyi = yongyi_data[month].get('hog_feed_yongyi')
        
        if month in ganglian_data:
            point.breeding_inventory_ganglian_nation = ganglian_data[month].get('breeding_inventory_ganglian_nation')
            point.piglet_inventory_ganglian_nation = ganglian_data[month].get('piglet_inventory_ganglian_nation')
            point.hog_inventory_ganglian_nation = ganglian_data[month].get('hog_inventory_ganglian_nation')
            point.breeding_feed_ganglian = ganglian_data[month].get('breeding_feed_ganglian')
            point.piglet_feed_ganglian = ganglian_data[month].get('piglet_feed_ganglian')
            point.hog_feed_ganglian = ganglian_data[month].get('hog_feed_ganglian')
        
        if month in cull_slaughter_data:
            point.cull_slaughter_yongyi = cull_slaughter_data[month].get('cull_slaughter_yongyi')
        
        data_points.append(point)
    
    latest_month = sorted_months[-1] if sorted_months else None
    
    return MultiSourceResponse(
        data=data_points,
        latest_month=latest_month
    )
