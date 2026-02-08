"""
E2. 多渠道汇总 API
包含3个表格：
1. 淘汰母猪屠宰环比、能繁母猪存栏环比、能繁母猪饲料环比
2. 新生仔猪存栏环比、仔猪饲料环比
3. 生猪存栏环比、育肥猪饲料环比
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import json
import math

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
                return datetime.fromisoformat(excel_date.replace('Z', '+00:00')).date()
            return datetime.strptime(excel_date, '%Y-%m-%d').date()
        except:
            pass
    elif isinstance(excel_date, date):
        return excel_date
    elif isinstance(excel_date, datetime):
        return excel_date.date()
    return None


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


def _calculate_month_on_month(values: List[float]) -> List[Optional[float]]:
    """计算环比"""
    result = []
    for i in range(len(values)):
        if i == 0:
            result.append(None)
        else:
            prev = values[i-1]
            curr = values[i]
            if prev is not None and curr is not None and not math.isnan(prev) and not math.isnan(curr) and prev != 0:
                mom = (curr - prev) / prev * 100
                if not math.isnan(mom) and not math.isinf(mom):
                    result.append(round(mom, 2))
                else:
                    result.append(None)
            else:
                result.append(None)
    return result


@router.get("/data", response_model=MultiSourceResponse)
async def get_multi_source_data(
    months: int = Query(10, description="显示最近N个月的数据"),
    db: Session = Depends(get_db)
):
    """
    获取多渠道汇总数据
    """
    # TODO: 实现数据获取逻辑
    # 由于数据源复杂，需要从多个raw_table读取数据并合并
    
    # 1. 获取淘汰母猪屠宰环比（涌益）
    cull_slaughter_data = _get_raw_table_data(db, "月度-淘汰母猪屠宰厂宰杀量")
    
    # 2. 获取能繁母猪存栏环比（涌益）
    breeding_inventory_data = _get_raw_table_data(db, "月度-能繁母猪存栏（2020年2月新增）")
    
    # 3. 获取能繁母猪饲料环比（涌益）
    feed_data = _get_raw_table_data(db, "月度-猪料销量")
    
    # 暂时返回空数据，待完善
    return MultiSourceResponse(
        data=[],
        latest_month=None
    )
