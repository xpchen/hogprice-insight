"""
E3. 供需曲线 API  (hogprice_v3 版)
包含3个图表：
1. 长周期生猪供需曲线（定点屠宰系数、猪价系数）
2. 能繁母猪存栏&猪价（滞后10个月）
3. 新生仔猪&猪价（滞后10个月）

数据源：hogprice_v3 数据库
  - fact_monthly_indicator  (NYB 环比、定点屠宰)
  - fact_price_daily        (钢联/涌益 全国猪价)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import math

from app.core.database import get_db

router = APIRouter(prefix="/api/v1/supply-demand", tags=["supply-demand"])


# ── Pydantic Models ──────────────────────────────────────────

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


# ── Helper: 全国猪价按月聚合 ──────────────────────────────────

def _get_national_monthly_price(db: Session) -> Dict[str, float]:
    """
    从 fact_price_daily 获取全国猪价，按月聚合为均值。
    优先级：GANGLIAN hog_avg_price > YONGYI 标猪均价
    返回 {YYYY-MM: avg_price}
    """
    # 尝试钢联全国猪价
    sql = text("""
        SELECT DATE_FORMAT(trade_date, '%Y-%m') AS ym,
               AVG(value) AS avg_price
        FROM fact_price_daily
        WHERE region_code = 'NATION'
          AND price_type = 'hog_avg_price'
          AND source = 'GANGLIAN'
          AND value IS NOT NULL
        GROUP BY ym
        ORDER BY ym
    """)
    rows = db.execute(sql).fetchall()

    price_by_month: Dict[str, float] = {}
    for r in rows:
        if r.avg_price is not None:
            price_by_month[r.ym] = float(r.avg_price)

    if price_by_month:
        return price_by_month

    # 备选：涌益标猪均价 (region_code='NATION')
    sql2 = text("""
        SELECT DATE_FORMAT(trade_date, '%Y-%m') AS ym,
               AVG(value) AS avg_price
        FROM fact_price_daily
        WHERE region_code = 'NATION'
          AND price_type = '标猪均价'
          AND source = 'YONGYI'
          AND value IS NOT NULL
        GROUP BY ym
        ORDER BY ym
    """)
    rows2 = db.execute(sql2).fetchall()
    for r in rows2:
        if r.avg_price is not None:
            price_by_month[r.ym] = float(r.avg_price)

    return price_by_month


# ── Helper: 定点屠宰月度数据 ─────────────────────────────────

def _get_designated_slaughter_monthly(db: Session) -> Dict[str, float]:
    """
    从 fact_monthly_indicator 获取定点屠宰量（绝对值）。
    indicator_code = 'designated_slaughter', value_type = 'abs'
    返回 {YYYY-MM: value}
    """
    sql = text("""
        SELECT DATE_FORMAT(month_date, '%Y-%m') AS ym,
               value
        FROM fact_monthly_indicator
        WHERE indicator_code = 'designated_slaughter'
          AND value_type = 'abs'
          AND region_code = 'NATION'
          AND value IS NOT NULL
          AND value > 0
        ORDER BY ym
    """)
    rows = db.execute(sql).fetchall()

    result: Dict[str, float] = {}
    for r in rows:
        result[r.ym] = float(r.value)

    return result


# ── Helper: 存栏环比 → 指数 ──────────────────────────────────

def _build_inventory_index(
    mom_by_month: Dict[str, float],
    base_year: int = 2020,
    base_month: int = 1,
    base_index: float = 80.0,
) -> List[dict]:
    """
    用环比百分比序列构建存栏指数。

    mom_by_month: {YYYY-MM: mom_pct}，例如 1.02 表示环比 +2%，
                  也可能是 102 (百分比)。导入时 NYB value_type='mom_pct',
                  值通常 < 2 表示比例（如 0.98），否则是百分比（如 98 ≈ -2%）。
    指数以 base_year-base_month 为 base_index。
    """
    base_ym = f"{base_year}-{base_month:02d}"
    sorted_months = sorted(mom_by_month.keys())

    result = []
    current_index = None

    for ym in sorted_months:
        if ym < base_ym:
            continue

        raw = mom_by_month[ym]

        # 判断 raw 是比例还是百分比
        # NYB 的 value_type='mom_pct' 存储的是环比百分比变化值（如 -2.5 表示 -2.5%）
        # 转成比例：mom_ratio = 1 + raw / 100
        if abs(raw) < 2:
            # 已经是比例形式（如 0.98 或 1.02）
            mom_ratio = raw
        else:
            # 百分比形式（如 -2.5 表示 -2.5%）
            mom_ratio = 1 + raw / 100

        if mom_ratio <= 0:
            continue

        if current_index is None:
            current_index = base_index
        else:
            current_index = current_index * mom_ratio

        result.append({
            "month": ym,
            "inventory_index": round(current_index, 2),
            "inventory_month": ym,
        })

    return result


# ══════════════════════════════════════════════════════════════
# Endpoint 1: 长周期生猪供需曲线
# ══════════════════════════════════════════════════════════════

@router.get("/curve", response_model=SupplyDemandCurveResponse)
async def get_supply_demand_curve(
    db: Session = Depends(get_db)
):
    """
    获取长周期生猪供需曲线数据
    屠宰系数 = 当月定点屠宰 / 该日历月历年均值
    价格系数 = 当月均价 / 该日历月历年均值
    """
    # 1. 定点屠宰（月度绝对值）
    slaughter_by_month = _get_designated_slaughter_monthly(db)

    # 2. 全国猪价（日度 → 月度均值）
    price_by_month = _get_national_monthly_price(db)

    if not slaughter_by_month and not price_by_month:
        return SupplyDemandCurveResponse(data=[], latest_month=None)

    # 3. 提取各自涵盖的年份
    slaughter_years = {int(ym[:4]) for ym in slaughter_by_month}
    price_years = {int(ym[:4]) for ym in price_by_month}
    common_years = slaughter_years & price_years
    if not common_years:
        common_years = slaughter_years | price_years

    # 4. 各日历月历年均值
    slaughter_avg_by_m: Dict[int, float] = {}
    price_avg_by_m: Dict[int, float] = {}
    for m in range(1, 13):
        s_vals = [slaughter_by_month[f"{y}-{m:02d}"]
                  for y in common_years if f"{y}-{m:02d}" in slaughter_by_month]
        p_vals = [price_by_month[f"{y}-{m:02d}"]
                  for y in common_years if f"{y}-{m:02d}" in price_by_month]
        if s_vals:
            slaughter_avg_by_m[m] = sum(s_vals) / len(s_vals)
        if p_vals:
            price_avg_by_m[m] = sum(p_vals) / len(p_vals)

    # 5. 计算系数
    all_months = sorted(set(list(slaughter_by_month.keys()) + list(price_by_month.keys())))
    result: List[SupplyDemandCurvePoint] = []

    for ym in all_months:
        parts = ym.split("-")
        if len(parts) != 2:
            continue
        try:
            month_num = int(parts[1])
        except ValueError:
            continue

        slaughter_coef = None
        price_coef = None

        if ym in slaughter_by_month and month_num in slaughter_avg_by_m:
            avg_s = slaughter_avg_by_m[month_num]
            if avg_s and avg_s > 0:
                slaughter_coef = round(slaughter_by_month[ym] / avg_s, 4)

        if ym in price_by_month and month_num in price_avg_by_m:
            avg_p = price_avg_by_m[month_num]
            if avg_p and avg_p > 0:
                price_coef = round(price_by_month[ym] / avg_p, 4)

        if slaughter_coef is not None or price_coef is not None:
            result.append(SupplyDemandCurvePoint(
                month=ym,
                slaughter_coefficient=slaughter_coef,
                price_coefficient=price_coef,
            ))

    latest = result[-1].month if result else None
    return SupplyDemandCurveResponse(data=result, latest_month=latest)


# ══════════════════════════════════════════════════════════════
# Endpoint 2: 能繁母猪存栏 & 猪价（滞后10个月）
# ══════════════════════════════════════════════════════════════

@router.get("/breeding-inventory-price", response_model=InventoryPriceResponse)
async def get_breeding_inventory_price(
    db: Session = Depends(get_db)
):
    """
    获取能繁母猪存栏&猪价（滞后10个月）
    能繁母猪存栏指数：以2020年1月为80，按照农业部(NYB)的环比累计计算
    数据来源：fact_monthly_indicator, indicator_code='breeding_sow_inventory',
              sub_category='nation', source='NYB', value_type='mom_pct'
    """
    # 1. 获取 NYB 能繁母猪环比数据
    sql = text("""
        SELECT DATE_FORMAT(month_date, '%Y-%m') AS ym,
               value
        FROM fact_monthly_indicator
        WHERE indicator_code = 'breeding_sow_inventory'
          AND sub_category = 'nation'
          AND source = 'NYB'
          AND value_type = 'mom_pct'
          AND value IS NOT NULL
        ORDER BY month_date
    """)
    rows = db.execute(sql).fetchall()

    if not rows:
        return InventoryPriceResponse(data=[], latest_month=None)

    mom_by_month: Dict[str, float] = {}
    for r in rows:
        mom_by_month[r.ym] = float(r.value)

    # 2. 计算存栏指数（以2020年1月为80）
    index_data = _build_inventory_index(mom_by_month)

    if not index_data:
        return InventoryPriceResponse(data=[], latest_month=None)

    # 3. 获取全国猪价（按月均值）
    price_by_month = _get_national_monthly_price(db)

    # 4. 合并数据（存栏月份 → 滞后10个月取对应猪价）
    final_result: List[InventoryPricePoint] = []
    for item in index_data:
        inv_month = item["inventory_month"]
        # 滞后10个月
        inv_date = datetime.strptime(inv_month + "-01", "%Y-%m-%d").date()
        price_date = inv_date + timedelta(days=300)  # 约10个月
        price_ym = price_date.strftime("%Y-%m")

        price = price_by_month.get(price_ym)

        final_result.append(InventoryPricePoint(
            month=inv_month,
            inventory_index=item["inventory_index"],
            price=round(price, 2) if price else None,
            inventory_month=inv_month,
        ))

    latest_month = final_result[-1].month if final_result else None
    return InventoryPriceResponse(data=final_result, latest_month=latest_month)


# ══════════════════════════════════════════════════════════════
# Endpoint 3: 新生仔猪存栏 & 猪价（滞后10个月）
# ══════════════════════════════════════════════════════════════

@router.get("/piglet-price", response_model=InventoryPriceResponse)
async def get_piglet_price(
    db: Session = Depends(get_db)
):
    """
    获取新生仔猪存栏&猪价（滞后10个月）
    新生仔猪存栏指数：以2020年1月为80，按照农业部(NYB)的环比累计计算
    数据来源：fact_monthly_indicator, indicator_code='piglet_inventory',
              sub_category='nation', source='NYB', value_type='mom_pct'
    """
    # 1. 获取 NYB 新生仔猪环比数据
    sql = text("""
        SELECT DATE_FORMAT(month_date, '%Y-%m') AS ym,
               value
        FROM fact_monthly_indicator
        WHERE indicator_code = 'piglet_inventory'
          AND sub_category = 'nation'
          AND source = 'NYB'
          AND value_type = 'mom_pct'
          AND value IS NOT NULL
        ORDER BY month_date
    """)
    rows = db.execute(sql).fetchall()

    if not rows:
        return InventoryPriceResponse(data=[], latest_month=None)

    mom_by_month: Dict[str, float] = {}
    for r in rows:
        mom_by_month[r.ym] = float(r.value)

    # 2. 计算存栏指数（以2020年1月为80）
    index_data = _build_inventory_index(mom_by_month)

    if not index_data:
        return InventoryPriceResponse(data=[], latest_month=None)

    # 3. 获取全国猪价（按月均值）
    price_by_month = _get_national_monthly_price(db)

    # 4. 合并数据（存栏月份 → 滞后10个月取对应猪价）
    final_result: List[InventoryPricePoint] = []
    for item in index_data:
        inv_month = item["inventory_month"]
        # 滞后10个月
        inv_date = datetime.strptime(inv_month + "-01", "%Y-%m-%d").date()
        price_date = inv_date + timedelta(days=300)  # 约10个月
        price_ym = price_date.strftime("%Y-%m")

        price = price_by_month.get(price_ym)

        final_result.append(InventoryPricePoint(
            month=inv_month,
            inventory_index=item["inventory_index"],
            price=round(price, 2) if price else None,
            inventory_month=inv_month,
        ))

    latest_month = final_result[-1].month if final_result else None
    return InventoryPriceResponse(data=final_result, latest_month=latest_month)
