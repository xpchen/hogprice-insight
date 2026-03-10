"""
价格展示API (hogprice_v3)
查询 fact_price_daily / fact_spread_daily / fact_slaughter_daily / dim_region 四张表。

提供图表数据接口：
1. 全国猪价（季节性）
2. 标肥价差（季节性）
3. 猪价&标肥价差（可年度筛选）
4. 日度屠宰量（农历）
5. 标肥价差（分省区）
6. 区域价差（季节性）
7. 毛白价差双轴
8. 冻品库容率（省份列表 / 季节性）  -- 新表中暂无，保留接口返回空
9. 产业链数据（周度）              -- 新表中暂无，保留接口返回空
10. 省份多指标面板
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys_user import SysUser
from app.services.lunar_alignment_service import (
    solar_to_lunar,
    get_lunar_year_date_range,
    get_leap_month_info,
    get_lunar_year_date_range_la_ba,
)

router = APIRouter(prefix="/api/v1/price-display", tags=["price-display"])


# ---------------------------------------------------------------------------
# Pydantic 响应模型（与前端约定保持不变）
# ---------------------------------------------------------------------------

class SeasonalityDataPoint(BaseModel):
    """季节性数据点"""
    year: int
    month_day: str  # "MM-DD" 格式
    value: Optional[float]
    lunar_day_index: Optional[int] = None


class SeasonalitySeries(BaseModel):
    """季节性数据系列"""
    year: int
    data: List[SeasonalityDataPoint]
    color: Optional[str] = None
    is_leap_month: Optional[bool] = False
    leap_month: Optional[int] = None


class SeasonalityResponse(BaseModel):
    """季节性数据响应"""
    metric_name: str
    unit: str
    series: List[SeasonalitySeries]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


class PriceSpreadResponse(BaseModel):
    """价格和价差响应"""
    price_data: List[Dict[str, Any]]
    spread_data: List[Dict[str, Any]]
    available_years: List[int]
    update_time: Optional[str] = None


class SlaughterLunarResponse(BaseModel):
    """日度屠宰量（农历）响应"""
    metric_name: str
    unit: str
    series: List[SeasonalitySeries]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None
    x_axis_labels: Optional[Dict[int, str]] = None


class SlaughterPriceTrendResponse(BaseModel):
    """屠宰量&价格走势响应（农历年度日期范围）"""
    slaughter_data: List[Dict[str, Any]]
    price_data: List[Dict[str, Any]]
    available_lunar_years: List[int]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


class SlaughterPriceTrendSolarResponse(BaseModel):
    """屠宰&价格 相关走势（按年，阳历日期 正月初八~腊月二十八）"""
    slaughter_data: List[Dict[str, Any]]
    price_data: List[Dict[str, Any]]
    available_years: List[int]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


class LiveWhiteSpreadDualAxisResponse(BaseModel):
    """毛白价差双轴数据响应"""
    spread_data: List[Dict[str, Any]]
    ratio_data: List[Dict[str, Any]]
    spread_unit: str
    ratio_unit: str
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


class ProvinceSpreadInfo(BaseModel):
    """省区标肥价差信息"""
    province_name: str
    province_code: Optional[str] = None
    metric_id: int = 0  # 兼容旧字段，新表无意义，固定 0
    latest_date: Optional[str] = None
    latest_value: Optional[float] = None


class ProvinceSpreadListResponse(BaseModel):
    """省区标肥价差列表响应"""
    provinces: List[ProvinceSpreadInfo]
    unit: str


class FrozenInventoryProvinceInfo(BaseModel):
    province_name: str
    metric_id: int = 0
    latest_date: Optional[str] = None
    latest_value: Optional[float] = None


class FrozenInventoryProvinceListResponse(BaseModel):
    provinces: List[FrozenInventoryProvinceInfo]
    unit: str


class FrozenInventorySeasonalityResponse(BaseModel):
    metric_name: str
    unit: str
    province_name: str
    series: List[SeasonalitySeries]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None
    period_change: Optional[float] = None
    yoy_change: Optional[float] = None


class IndustryChainSeasonalityResponse(BaseModel):
    metric_name: str
    unit: str
    series: List[SeasonalitySeries]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None
    period_change: Optional[float] = None
    yoy_change: Optional[float] = None


class ProvinceIndicatorsResponse(BaseModel):
    province_name: str
    indicators: Dict[str, SeasonalityResponse]


# ---------------------------------------------------------------------------
# 通用辅助函数
# ---------------------------------------------------------------------------

def _rows_to_daily_seasonality(
    rows,
    *,
    date_col: str = "trade_date",
    value_col: str = "value",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> Tuple[List[SeasonalitySeries], Optional[str]]:
    """将 (trade_date, value) 行列表转为按年分组的 SeasonalitySeries 列表。"""
    year_data: Dict[int, List[Dict]] = {}
    for row in rows:
        d = row._mapping[date_col] if hasattr(row, '_mapping') else row[date_col]
        v = row._mapping[value_col] if hasattr(row, '_mapping') else row[value_col]
        if d is None:
            continue
        year = d.year
        if start_year and year < start_year:
            continue
        if end_year and year > end_year:
            continue
        if year not in year_data:
            year_data[year] = []
        year_data[year].append({
            "month_day": d.strftime("%m-%d"),
            "value": float(v) if v is not None else None,
            "date": d,
        })

    series: List[SeasonalitySeries] = []
    for year in sorted(year_data.keys()):
        data_points = [
            SeasonalityDataPoint(year=year, month_day=item["month_day"], value=item["value"])
            for item in sorted(year_data[year], key=lambda x: x["date"])
        ]
        series.append(SeasonalitySeries(year=year, data=data_points))

    latest_date: Optional[str] = None
    if rows:
        last_row = rows[-1]
        d = last_row._mapping[date_col] if hasattr(last_row, '_mapping') else last_row[date_col]
        if d:
            latest_date = d.isoformat()
    return series, latest_date


def _rows_to_weekly_seasonality(
    rows,
    *,
    date_col: str = "trade_date",
    value_col: str = "value",
) -> Tuple[List[SeasonalitySeries], Optional[str]]:
    """将周度 (trade_date, value) 行列表按 ISO 周号分组为季节性曲线。"""
    year_data: Dict[int, Dict[int, List[float]]] = {}
    for row in rows:
        d = row._mapping[date_col] if hasattr(row, '_mapping') else row[date_col]
        v = row._mapping[value_col] if hasattr(row, '_mapping') else row[value_col]
        if d is None:
            continue
        year = d.year
        week = max(1, min(52, d.isocalendar()[1]))
        if year not in year_data:
            year_data[year] = {}
        if week not in year_data[year]:
            year_data[year][week] = []
        if v is not None:
            year_data[year][week].append(float(v))

    series: List[SeasonalitySeries] = []
    for year in sorted(year_data.keys()):
        data_points = []
        for week in range(1, 53):
            vals = year_data[year].get(week, [])
            value = (sum(vals) / len(vals)) if vals else None
            jan1 = datetime(year, 1, 1)
            days_offset = (week - 1) * 7 - jan1.weekday()
            week_start = jan1 + timedelta(days=days_offset)
            month_day = week_start.strftime("%m-%d")
            data_points.append(SeasonalityDataPoint(year=year, month_day=month_day, value=value))
        series.append(SeasonalitySeries(year=year, data=data_points))

    latest_date: Optional[str] = None
    if rows:
        last_row = rows[-1]
        d = last_row._mapping[date_col] if hasattr(last_row, '_mapping') else last_row[date_col]
        if d:
            latest_date = d.isoformat()
    return series, latest_date


def _resolve_region_code(db: Session, province_name: str) -> Optional[str]:
    """根据省份名称在 dim_region 中查找 region_code。"""
    row = db.execute(
        text("SELECT region_code FROM dim_region WHERE region_name = :name LIMIT 1"),
        {"name": province_name},
    ).first()
    return row[0] if row else None


def _compute_changes(
    db: Session,
    table: str,
    type_col: str,
    type_val: str,
    region_code: str = "NATION",
    extra_filter: str = "",
) -> Dict[str, Any]:
    """通用涨跌计算：5 日 / 10 日变化。"""
    sql = f"""
        SELECT trade_date, value FROM {table}
        WHERE {type_col} = :type_val AND region_code = :rc {extra_filter}
        ORDER BY trade_date DESC LIMIT 11
    """
    rows = db.execute(text(sql), {"type_val": type_val, "rc": region_code}).fetchall()
    if not rows:
        return {"current_value": None, "latest_date": None, "day5_change": None, "day10_change": None, "unit": "元/公斤"}

    latest_date = rows[0][0]
    latest_value = float(rows[0][1]) if rows[0][1] is not None else None

    day5_date = date.fromordinal(latest_date.toordinal() - 5)
    day10_date = date.fromordinal(latest_date.toordinal() - 10)

    def _find_val(target: date):
        sql2 = f"""
            SELECT value FROM {table}
            WHERE {type_col} = :type_val AND region_code = :rc {extra_filter}
              AND trade_date = :td LIMIT 1
        """
        r = db.execute(text(sql2), {"type_val": type_val, "rc": region_code, "td": target}).first()
        return float(r[0]) if r and r[0] is not None else None

    d5v = _find_val(day5_date)
    d10v = _find_val(day10_date)

    return {
        "current_value": latest_value,
        "latest_date": latest_date.isoformat(),
        "day5_change": (latest_value - d5v) if latest_value is not None and d5v is not None else None,
        "day10_change": (latest_value - d10v) if latest_value is not None and d10v is not None else None,
        "unit": "元/公斤",
    }


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.get("/test")
async def test_price_display():
    """测试端点"""
    return {"status": "ok", "message": "Price display API is working"}


# ========================== 屠宰&价格走势（农历年度）==========================

@router.get("/slaughter-price-trend/lunar-year", response_model=SlaughterPriceTrendResponse)
async def get_slaughter_price_trend_lunar_year(
    lunar_year: Optional[int] = Query(None, description="农历年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """屠宰量&价格走势数据（农历年度日期范围，每年 2/20 ~ 次年 2/10）"""
    current_solar_year = datetime.now().year
    lunar_years_to_check = list(range(current_solar_year - 2, current_solar_year + 3))

    valid_lunar_years: List[int] = []
    lunar_year_ranges: Dict[int, Tuple[date, date]] = {}
    for check_year in lunar_years_to_check:
        dr = get_lunar_year_date_range(check_year)
        if dr:
            valid_lunar_years.append(check_year)
            lunar_year_ranges[check_year] = dr

    if not valid_lunar_years:
        return SlaughterPriceTrendResponse(
            slaughter_data=[], price_data=[], available_lunar_years=[], update_time=None, latest_date=None
        )

    if lunar_year is not None:
        if lunar_year not in valid_lunar_years:
            raise HTTPException(status_code=400, detail=f"农历年份{lunar_year}不符合条件或没有数据")
        valid_lunar_years = [lunar_year]

    all_start = min(r[0] for r in lunar_year_ranges.values())
    all_end = max(r[1] for r in lunar_year_ranges.values())

    slaughter_rows = db.execute(
        text("""
            SELECT trade_date, volume FROM fact_slaughter_daily
            WHERE region_code = 'NATION' AND source = 'YONGYI'
              AND trade_date BETWEEN :s AND :e
            ORDER BY trade_date
        """),
        {"s": all_start, "e": all_end},
    ).fetchall()

    price_rows = db.execute(
        text("""
            SELECT trade_date, value FROM fact_price_daily
            WHERE price_type = '标猪均价' AND region_code = 'NATION' AND source = 'YONGYI'
              AND trade_date BETWEEN :s AND :e
            ORDER BY trade_date
        """),
        {"s": all_start, "e": all_end},
    ).fetchall()
    if not price_rows:
        price_rows = db.execute(
            text("""
                SELECT trade_date, value FROM fact_price_daily
                WHERE price_type = '全国均价' AND region_code = 'NATION' AND source = 'YONGYI'
                  AND trade_date BETWEEN :s AND :e
                ORDER BY trade_date
            """),
            {"s": all_start, "e": all_end},
        ).fetchall()
    if not price_rows:
        price_rows = db.execute(
            text("""
                SELECT trade_date, value FROM fact_price_daily
                WHERE price_type = 'hog_avg_price' AND region_code = 'NATION' AND source = 'GANGLIAN'
                  AND trade_date BETWEEN :s AND :e
                ORDER BY trade_date
            """),
            {"s": all_start, "e": all_end},
        ).fetchall()

    slaughter_data: List[Dict[str, Any]] = []
    price_data: List[Dict[str, Any]] = []

    for ly in valid_lunar_years:
        sd, ed = lunar_year_ranges[ly]
        for row in slaughter_rows:
            d, v = row[0], row[1]
            if sd <= d <= ed:
                slaughter_data.append({"date": d.isoformat(), "year": ly, "value": float(v) if v is not None else None})
        for row in price_rows:
            d, v = row[0], row[1]
            if sd <= d <= ed:
                price_data.append({"date": d.isoformat(), "year": ly, "value": float(v) if v is not None else None})

    latest_date = slaughter_rows[-1][0].isoformat() if slaughter_rows else (price_rows[-1][0].isoformat() if price_rows else None)

    return SlaughterPriceTrendResponse(
        slaughter_data=slaughter_data,
        price_data=price_data,
        available_lunar_years=valid_lunar_years,
        update_time=latest_date,
        latest_date=latest_date,
    )


# ========================== 标肥价差（分省区）==========================

@router.get("/fat-std-spread/provinces", response_model=ProvinceSpreadListResponse)
async def get_fat_std_spread_provinces(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取所有有标肥价差数据的省区列表"""
    rows = db.execute(text("""
        SELECT s.region_code, r.region_name,
               MAX(s.trade_date) AS latest_date,
               (SELECT s2.value FROM fact_spread_daily s2
                WHERE s2.region_code = s.region_code AND s2.spread_type = 'fat_std_spread'
                ORDER BY s2.trade_date DESC LIMIT 1) AS latest_value
        FROM fact_spread_daily s
        JOIN dim_region r ON r.region_code = s.region_code
        WHERE s.spread_type = 'fat_std_spread' AND s.region_code <> 'NATION'
        GROUP BY s.region_code, r.region_name
        ORDER BY r.region_name
    """)).fetchall()

    provinces = [
        ProvinceSpreadInfo(
            province_name=row[1],
            province_code=row[0],
            latest_date=row[2].isoformat() if row[2] else None,
            latest_value=float(row[3]) if row[3] is not None else None,
        )
        for row in rows
    ]
    return ProvinceSpreadListResponse(provinces=provinces, unit="元/公斤")


@router.get("/fat-std-spread/province/{province_name}/seasonality", response_model=SeasonalityResponse)
async def get_fat_std_spread_province_seasonality(
    province_name: str,
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取指定省区的标肥价差季节性数据"""
    rc = _resolve_region_code(db, province_name)
    if not rc:
        raise HTTPException(status_code=404, detail=f"未找到省份：{province_name}")

    params: Dict[str, Any] = {"rc": rc, "st": "fat_std_spread"}
    sql = "SELECT trade_date, value FROM fact_spread_daily WHERE spread_type = :st AND region_code = :rc"
    if start_year:
        sql += " AND YEAR(trade_date) >= :sy"
        params["sy"] = start_year
    if end_year:
        sql += " AND YEAR(trade_date) <= :ey"
        params["ey"] = end_year
    sql += " ORDER BY trade_date"

    rows = db.execute(text(sql), params).fetchall()
    series, latest = _rows_to_daily_seasonality(rows, start_year=start_year, end_year=end_year)

    return SeasonalityResponse(
        metric_name=f"{province_name}标肥价差",
        unit="元/公斤",
        series=series,
        update_time=latest,
        latest_date=latest,
    )


@router.get("/fat-std-spread/province/{province_name}/changes")
async def get_fat_std_spread_province_changes(
    province_name: str,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取指定省区标肥价差的涨跌数据"""
    rc = _resolve_region_code(db, province_name)
    if not rc:
        raise HTTPException(status_code=404, detail=f"未找到省份：{province_name}")
    return _compute_changes(db, "fact_spread_daily", "spread_type", "fat_std_spread", region_code=rc)


# ========================== 区域价差（季节性 & 涨跌）==========================

@router.get("/region-spread/seasonality", response_model=SeasonalityResponse)
async def get_region_spread_seasonality(
    region_pair: str = Query(..., description="区域对，格式：XX-YY，如'广东-广西'"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取区域价差季节性数据"""
    regions = region_pair.split("-")
    if len(regions) != 2:
        raise HTTPException(status_code=400, detail="区域对格式错误，应为'XX-YY'格式")

    r1, r2 = regions[0].strip(), regions[1].strip()
    # 中文省名 → 英文 code 映射
    from import_tool.utils import PROVINCE_TO_CODE
    r1_code = PROVINCE_TO_CODE.get(r1, r1).upper()
    r2_code = PROVINCE_TO_CODE.get(r2, r2).upper()

    # 精确匹配 spread_type = region_spread_XX_YY
    spread_type_exact = f"region_spread_{r1_code}_{r2_code}"
    st_row = db.execute(
        text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type = :st LIMIT 1"),
        {"st": spread_type_exact},
    ).first()
    if not st_row:
        # 反方向试试
        spread_type_exact2 = f"region_spread_{r2_code}_{r1_code}"
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type = :st LIMIT 1"),
            {"st": spread_type_exact2},
        ).first()
    if not st_row:
        # 兼容历史错误拼写：spread_type 曾为 VARCHAR(32)，重庆被存成 CHONGQIN
        if (r1_code, r2_code) == ("GUANGDONG", "CHONGQING"):
            st_row = db.execute(
                text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type = 'region_spread_GUANGDONG_CHONGQIN' LIMIT 1"),
            ).first()
        elif (r2_code, r1_code) == ("GUANGDONG", "CHONGQING"):
            st_row = db.execute(
                text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type = 'region_spread_CHONGQIN_GUANGDONG' LIMIT 1"),
            ).first()
    if not st_row:
        # 前缀匹配：兼容其它拼写变体
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type LIKE :stl LIMIT 1"),
            {"stl": f"region_spread_{r1_code}_{r2_code}%"},
        ).first()
    if not st_row:
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type LIKE :stl LIMIT 1"),
            {"stl": f"region_spread_{r2_code}_{r1_code}%"},
        ).first()
    if not st_row:
        # 降级到 LIKE 含两省 code
        spread_type_like = f"region_spread_%{r1_code}%{r2_code}%"
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type LIKE :stl LIMIT 1"),
            {"stl": spread_type_like},
        ).first()
    if not st_row:
        raise HTTPException(status_code=404, detail=f"未找到区域价差指标：{region_pair}")

    spread_type = st_row[0]
    sql_params: Dict[str, Any] = {"st": spread_type}
    sql = "SELECT trade_date, value FROM fact_spread_daily WHERE spread_type = :st"
    if start_year:
        sql += " AND YEAR(trade_date) >= :sy"
        sql_params["sy"] = start_year
    if end_year:
        sql += " AND YEAR(trade_date) <= :ey"
        sql_params["ey"] = end_year
    sql += " ORDER BY trade_date"

    rows = db.execute(text(sql), sql_params).fetchall()
    series, latest = _rows_to_daily_seasonality(rows, start_year=start_year, end_year=end_year)

    return SeasonalityResponse(
        metric_name=f"{r1}-{r2}区域价差",
        unit="元/公斤",
        series=series,
        update_time=latest,
        latest_date=latest,
    )


@router.get("/region-spread/changes")
async def get_region_spread_changes(
    region_pair: str = Query(..., description="区域对，格式：XX-YY"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取区域价差的涨跌数据"""
    regions = region_pair.split("-")
    if len(regions) != 2:
        raise HTTPException(status_code=400, detail="区域对格式错误，应为'XX-YY'格式")

    r1, r2 = regions[0].strip(), regions[1].strip()
    from import_tool.utils import PROVINCE_TO_CODE
    r1_code = PROVINCE_TO_CODE.get(r1, r1).upper()
    r2_code = PROVINCE_TO_CODE.get(r2, r2).upper()
    spread_type_exact = f"region_spread_{r1_code}_{r2_code}"
    st_row = db.execute(
        text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type = :st LIMIT 1"),
        {"st": spread_type_exact},
    ).first()
    if not st_row:
        spread_type_exact2 = f"region_spread_{r2_code}_{r1_code}"
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type = :st LIMIT 1"),
            {"st": spread_type_exact2},
        ).first()
    if not st_row and (r1_code, r2_code) == ("GUANGDONG", "CHONGQING"):
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type = 'region_spread_GUANGDONG_CHONGQIN' LIMIT 1"),
        ).first()
    if not st_row and (r2_code, r1_code) == ("GUANGDONG", "CHONGQING"):
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type = 'region_spread_CHONGQIN_GUANGDONG' LIMIT 1"),
        ).first()
    if not st_row:
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type LIKE :stl LIMIT 1"),
            {"stl": f"region_spread_{r1_code}_{r2_code}%"},
        ).first()
    if not st_row:
        st_row = db.execute(
            text("SELECT DISTINCT spread_type FROM fact_spread_daily WHERE spread_type LIKE :stl LIMIT 1"),
            {"stl": f"region_spread_{r2_code}_{r1_code}%"},
        ).first()
    if not st_row:
        raise HTTPException(status_code=404, detail=f"未找到区域价差指标：{region_pair}")

    return _compute_changes(db, "fact_spread_daily", "spread_type", st_row[0])


# ========================== 毛白价差双轴 ==========================

@router.get("/live-white-spread/dual-axis", response_model=LiveWhiteSpreadDualAxisResponse)
async def get_live_white_spread_dual_axis(
    start_date: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """毛白价差 + 价差比率双轴"""
    # 毛白价差
    spread_sql = """
        SELECT trade_date, value FROM fact_spread_daily
        WHERE spread_type = 'mao_bai_spread' AND region_code = 'NATION'
    """
    params: Dict[str, Any] = {}
    if start_date:
        spread_sql += " AND trade_date >= :sd"
        params["sd"] = start_date
    if end_date:
        spread_sql += " AND trade_date <= :ed"
        params["ed"] = end_date
    spread_sql += " ORDER BY trade_date"
    spread_rows = db.execute(text(spread_sql), params).fetchall()

    # 价差比率 = 毛白价差 / 毛猪价格。如表中有 'mao_bai_ratio' 则直接取，否则计算。
    ratio_sql = """
        SELECT trade_date, value FROM fact_spread_daily
        WHERE spread_type = 'mao_bai_ratio' AND region_code = 'NATION'
    """
    if start_date:
        ratio_sql += " AND trade_date >= :sd"
    if end_date:
        ratio_sql += " AND trade_date <= :ed"
    ratio_sql += " ORDER BY trade_date"
    ratio_rows = db.execute(text(ratio_sql), params).fetchall()

    # 如果没有预算的 ratio，从毛白价差和生猪价格手动计算
    if not ratio_rows:
        price_sql = """
            SELECT trade_date, value FROM fact_price_daily
            WHERE price_type = 'hog_avg_price' AND region_code = 'NATION' AND source = 'GANGLIAN'
        """
        if start_date:
            price_sql += " AND trade_date >= :sd"
        if end_date:
            price_sql += " AND trade_date <= :ed"
        price_sql += " ORDER BY trade_date"
        price_rows = db.execute(text(price_sql), params).fetchall()

        price_map = {r[0]: float(r[1]) for r in price_rows if r[1] is not None}
        ratio_rows_computed = []
        for r in spread_rows:
            d, v = r[0], r[1]
            if v is not None and d in price_map and price_map[d] != 0:
                ratio_rows_computed.append({"date": d.isoformat(), "value": round(float(v) / price_map[d], 4)})
            else:
                ratio_rows_computed.append({"date": d.isoformat(), "value": None})
        ratio_data = ratio_rows_computed
    else:
        ratio_data = [
            {"date": r[0].isoformat(), "value": float(r[1]) if r[1] is not None else None}
            for r in ratio_rows
        ]

    spread_data = [
        {"date": r[0].isoformat(), "value": float(r[1]) if r[1] is not None else None}
        for r in spread_rows
    ]

    latest = spread_rows[-1][0].isoformat() if spread_rows else None

    return LiveWhiteSpreadDualAxisResponse(
        spread_data=spread_data,
        ratio_data=ratio_data,
        spread_unit="元/公斤",
        ratio_unit="元/公斤",
        update_time=latest,
        latest_date=latest,
    )


# ========================== 冻品库容率 ==========================

@router.get("/frozen-inventory/provinces", response_model=FrozenInventoryProvinceListResponse)
async def get_frozen_inventory_provinces(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取所有有冻品库容率数据的省份列表"""
    rows = db.execute(text("""
        SELECT w.region_code, r.region_name,
               MAX(w.week_end) AS latest_date,
               (SELECT w2.value FROM fact_weekly_indicator w2
                WHERE w2.region_code = w.region_code AND w2.indicator_code = 'frozen_rate'
                ORDER BY w2.week_end DESC LIMIT 1) AS latest_value
        FROM fact_weekly_indicator w
        JOIN dim_region r ON r.region_code = w.region_code
        WHERE w.indicator_code = 'frozen_rate' AND w.region_code <> 'NATION'
        GROUP BY w.region_code, r.region_name
        ORDER BY r.region_name
    """)).fetchall()
    provinces = [
        FrozenInventoryProvinceInfo(
            province_name=r.region_name,
            latest_date=r.latest_date.isoformat() if r.latest_date else None,
            latest_value=float(r.latest_value) if r.latest_value else None,
        )
        for r in rows
    ]
    return FrozenInventoryProvinceListResponse(provinces=provinces, unit="%")


@router.get("/frozen-inventory/province/{province_name}/seasonality", response_model=FrozenInventorySeasonalityResponse)
async def get_frozen_inventory_province_seasonality(
    province_name: str,
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """指定省份冻品库容率季节性"""
    rc = _resolve_region_code(db, province_name)
    if not rc:
        return FrozenInventorySeasonalityResponse(
            metric_name="冻品库容率", unit="%", province_name=province_name,
            series=[], update_time=None, latest_date=None, period_change=None, yoy_change=None,
        )

    _end = end_year if end_year is not None else date.today().year
    _start = start_year if start_year is not None else (_end - 5)

    rows = db.execute(
        text("""
            SELECT week_end AS trade_date, value FROM fact_weekly_indicator
            WHERE indicator_code = 'frozen_rate' AND region_code = :rc
              AND YEAR(week_end) BETWEEN :sy AND :ey
            ORDER BY week_end
        """),
        {"rc": rc, "sy": _start, "ey": _end},
    ).fetchall()

    series, latest = _rows_to_weekly_seasonality(rows)
    return FrozenInventorySeasonalityResponse(
        metric_name="冻品库容率",
        unit="%",
        province_name=province_name,
        series=series,
        update_time=latest,
        latest_date=latest,
        period_change=None,
        yoy_change=None,
    )


# ========================== 产业链数据（周度）==========================

# 中文指标名 → (indicator_code, unit) 映射
INDUSTRY_CHAIN_METRIC_MAP: Dict[str, Tuple[str, str]] = {
    "仔猪价格": ("piglet_price", "元/头"),
    "淘汰母猪折扣率": ("cull_sow_std_ratio", "%"),
    "屠宰利润": ("slaughter_profit", "元/头"),
    "自养利润": ("external_purchase_profit", "元/头"),
    "外购仔猪利润": ("external_purchase_profit", "元/头"),
    "代养利润": ("profit_contract_farming", "元/头"),
    "仔猪价格(15kg)": ("piglet_price_15kg", "元/头"),
    "出栏均重": ("weight_avg", "公斤"),
    "宰后均重": ("post_slaughter_weight", "公斤"),
    "冻品库容率": ("frozen_storage_rate", "%"),
    "猪粮比": ("pig_grain_ratio", ""),
    "猪料比": ("pig_feed_ratio", ""),
    "二元母猪价格": ("gilt_price", "元/头"),
    "淘汰母猪价格": ("cull_sow_price", "元/头"),
    "白条价格": ("carcass_top3_price_wavg", "元/公斤"),
    "1#鲜肉价格": ("fresh_pork_no1_price", "元/公斤"),
    "2#冻肉价格": ("frozen_no2_price_wavg", "元/公斤"),
    "4#冻肉价格": ("frozen_no4_price_wavg", "元/公斤"),
}

# 比率指标：分子 indicator_code / 分母 indicator_code
INDUSTRY_CHAIN_RATIO_MAP: Dict[str, Tuple[str, str]] = {
    "2号冻肉/1#鲜肉": ("frozen_no2_price_wavg", "fresh_pork_no1_price"),
    "4#冻肉/白条": ("frozen_no4_price_wavg", "carcass_top3_price_wavg"),
}


@router.get("/industry-chain/seasonality", response_model=IndustryChainSeasonalityResponse)
async def get_industry_chain_seasonality(
    metric_name: str = Query(..., description="指标名称"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """产业链数据季节性（周度 1-52 周），从 fact_weekly_indicator 查询。"""
    _end = end_year if end_year is not None else date.today().year
    _start = start_year if start_year is not None else (_end - 5)

    # 比率指标：分子/分母 两条时序按日期对齐后计算
    ratio_def = INDUSTRY_CHAIN_RATIO_MAP.get(metric_name)
    if ratio_def:
        num_code, den_code = ratio_def
        num_rows = db.execute(
            text("""
                SELECT week_end AS trade_date, value FROM fact_weekly_indicator
                WHERE indicator_code = :ic AND region_code = 'NATION'
                  AND YEAR(week_end) BETWEEN :sy AND :ey
                ORDER BY week_end
            """), {"ic": num_code, "sy": _start, "ey": _end},
        ).fetchall()
        den_rows = db.execute(
            text("""
                SELECT week_end AS trade_date, value FROM fact_weekly_indicator
                WHERE indicator_code = :ic AND region_code = 'NATION'
                  AND YEAR(week_end) BETWEEN :sy AND :ey
                ORDER BY week_end
            """), {"ic": den_code, "sy": _start, "ey": _end},
        ).fetchall()
        den_map = {r.trade_date: float(r.value) for r in den_rows if r.value}
        rows = []
        for r in num_rows:
            d = den_map.get(r.trade_date)
            if r.value and d and d != 0:
                rows.append({"trade_date": r.trade_date, "value": round(float(r.value) / d, 4)})
        series, latest = _rows_to_weekly_seasonality(rows)
        return IndustryChainSeasonalityResponse(
            metric_name=metric_name, unit="", series=series,
            update_time=latest, latest_date=latest, period_change=None, yoy_change=None,
        )

    # 普通指标
    mapping = INDUSTRY_CHAIN_METRIC_MAP.get(metric_name)
    if not mapping:
        return IndustryChainSeasonalityResponse(
            metric_name=metric_name, unit="-", series=[],
            update_time=None, latest_date=None, period_change=None, yoy_change=None,
        )

    indicator_code, unit = mapping

    rows = db.execute(
        text("""
            SELECT week_end AS trade_date, value
            FROM fact_weekly_indicator
            WHERE indicator_code = :ic AND region_code = 'NATION'
              AND YEAR(week_end) BETWEEN :sy AND :ey
            ORDER BY week_end
        """),
        {"ic": indicator_code, "sy": _start, "ey": _end},
    ).fetchall()

    series, latest = _rows_to_weekly_seasonality(rows)
    return IndustryChainSeasonalityResponse(
        metric_name=metric_name,
        unit=unit,
        series=series,
        update_time=latest,
        latest_date=latest,
        period_change=None,
        yoy_change=None,
    )


# ========================== 省份多指标面板 ==========================

@router.get("/province-indicators/{province_name}/seasonality", response_model=ProvinceIndicatorsResponse)
async def get_province_indicators_seasonality(
    province_name: str,
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    获取指定省份的多指标季节性数据。
    新表可提供：日度均价、日度散户标肥价差。
    周度出栏均重 / 宰后均重 / 90KG占比 / 冻品库容 暂无数据，跳过。
    """
    indicators_data: Dict[str, SeasonalityResponse] = {}
    rc = _resolve_region_code(db, province_name)

    # 1. 日度 均价 (fact_price_daily, price_type='省份均价')
    if rc:
        try:
            params: Dict[str, Any] = {"rc": rc, "pt": "省份均价"}
            sql = "SELECT trade_date, value FROM fact_price_daily WHERE price_type = :pt AND region_code = :rc"
            if start_year:
                sql += " AND YEAR(trade_date) >= :sy"
                params["sy"] = start_year
            if end_year:
                sql += " AND YEAR(trade_date) <= :ey"
                params["ey"] = end_year
            sql += " ORDER BY trade_date"
            rows = db.execute(text(sql), params).fetchall()
            if rows:
                series, latest = _rows_to_daily_seasonality(rows)
                indicators_data["日度 均价"] = SeasonalityResponse(
                    metric_name=f"{province_name}均价",
                    unit="元/公斤",
                    series=series,
                    update_time=latest,
                    latest_date=latest,
                )
        except Exception as e:
            print(f"获取日度均价失败: {e}")

    # 2. 日度 散户标肥价差 (fact_spread_daily, spread_type='fat_std_spread')
    if rc:
        try:
            params2: Dict[str, Any] = {"rc": rc, "st": "fat_std_spread"}
            sql2 = "SELECT trade_date, value FROM fact_spread_daily WHERE spread_type = :st AND region_code = :rc"
            if start_year:
                sql2 += " AND YEAR(trade_date) >= :sy"
                params2["sy"] = start_year
            if end_year:
                sql2 += " AND YEAR(trade_date) <= :ey"
                params2["ey"] = end_year
            sql2 += " ORDER BY trade_date"
            rows2 = db.execute(text(sql2), params2).fetchall()
            if rows2:
                series2, latest2 = _rows_to_daily_seasonality(rows2)
                indicators_data["日度 散户标肥价差"] = SeasonalityResponse(
                    metric_name=f"{province_name}散户标肥价差",
                    unit="元/公斤",
                    series=series2,
                    update_time=latest2,
                    latest_date=latest2,
                )
        except Exception as e:
            print(f"获取日度散户标肥价差失败: {e}")

    # 3. 周度 出栏均重 (fact_weekly_indicator, indicator_code='weight_avg')
    if rc:
        try:
            params3: Dict[str, Any] = {"rc": rc, "ic": "weight_avg"}
            sql3 = "SELECT week_end AS trade_date, value FROM fact_weekly_indicator WHERE indicator_code = :ic AND region_code = :rc"
            if start_year:
                sql3 += " AND YEAR(week_end) >= :sy"
                params3["sy"] = start_year
            if end_year:
                sql3 += " AND YEAR(week_end) <= :ey"
                params3["ey"] = end_year
            sql3 += " ORDER BY week_end"
            rows3 = db.execute(text(sql3), params3).fetchall()
            if rows3:
                series3, latest3 = _rows_to_weekly_seasonality(rows3)
                indicators_data["周度 出栏均重"] = SeasonalityResponse(
                    metric_name=f"{province_name}出栏均重",
                    unit="公斤",
                    series=series3,
                    update_time=latest3,
                    latest_date=latest3,
                )
        except Exception as e:
            print(f"获取周度出栏均重失败: {e}")

    # 4. 周度 宰后均重
    if rc:
        try:
            params4: Dict[str, Any] = {"rc": rc, "ic": "post_slaughter_weight"}
            sql4 = "SELECT week_end AS trade_date, value FROM fact_weekly_indicator WHERE indicator_code = :ic AND region_code = :rc"
            if start_year:
                sql4 += " AND YEAR(week_end) >= :sy"
                params4["sy"] = start_year
            if end_year:
                sql4 += " AND YEAR(week_end) <= :ey"
                params4["ey"] = end_year
            sql4 += " ORDER BY week_end"
            rows4 = db.execute(text(sql4), params4).fetchall()
            if rows4:
                series4, latest4 = _rows_to_weekly_seasonality(rows4)
                indicators_data["周度 宰后均重"] = SeasonalityResponse(
                    metric_name=f"{province_name}宰后均重",
                    unit="公斤",
                    series=series4,
                    update_time=latest4,
                    latest_date=latest4,
                )
        except Exception as e:
            print(f"获取周度宰后均重失败: {e}")

    # 5. 周度 90KG占比 (fact_weekly_indicator, indicator_code='weight_pct_under90')
    if rc:
        try:
            params5: Dict[str, Any] = {"rc": rc, "ic": "weight_pct_under90"}
            sql5 = "SELECT week_end AS trade_date, value FROM fact_weekly_indicator WHERE indicator_code = :ic AND region_code = :rc"
            if start_year:
                sql5 += " AND YEAR(week_end) >= :sy"
                params5["sy"] = start_year
            if end_year:
                sql5 += " AND YEAR(week_end) <= :ey"
                params5["ey"] = end_year
            sql5 += " ORDER BY week_end"
            rows5 = db.execute(text(sql5), params5).fetchall()
            if rows5:
                series5, latest5 = _rows_to_weekly_seasonality(rows5)
                indicators_data["周度 90KG占比"] = SeasonalityResponse(
                    metric_name=f"{province_name}90KG占比",
                    unit="%",
                    series=series5,
                    update_time=latest5,
                    latest_date=latest5,
                )
        except Exception as e:
            print(f"获取周度90KG占比失败: {e}")

    # 6. 周度 冻品库容 (fact_weekly_indicator, indicator_code='frozen_rate')
    if rc:
        try:
            params6: Dict[str, Any] = {"rc": rc, "ic": "frozen_rate"}
            sql6 = "SELECT week_end AS trade_date, value FROM fact_weekly_indicator WHERE indicator_code = :ic AND region_code = :rc"
            if start_year:
                sql6 += " AND YEAR(week_end) >= :sy"
                params6["sy"] = start_year
            if end_year:
                sql6 += " AND YEAR(week_end) <= :ey"
                params6["ey"] = end_year
            sql6 += " ORDER BY week_end"
            rows6 = db.execute(text(sql6), params6).fetchall()
            if rows6:
                series6, latest6 = _rows_to_weekly_seasonality(rows6)
                indicators_data["周度 冻品库容"] = SeasonalityResponse(
                    metric_name=f"{province_name}冻品库容",
                    unit="%",
                    series=series6,
                    update_time=latest6,
                    latest_date=latest6,
                )
        except Exception as e:
            print(f"获取周度冻品库容失败: {e}")

    return ProvinceIndicatorsResponse(province_name=province_name, indicators=indicators_data)


# ========================== price_national 子路由 ==========================
# 以下端点原来在 price_national.py 中，现在统一到此文件。

@router.get("/national-price/seasonality", response_model=SeasonalityResponse)
async def get_national_price_seasonality(
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """全国猪价季节性（按年对齐）
    优先级：标猪均价 > 全国均价 > hog_avg_price(GANGLIAN)。
    标猪均价仅有 2024-2026，缺少年份用全国均价补充以覆盖 2022-2026。
    """
    _end = end_year if end_year is not None else date.today().year
    _start = start_year if start_year is not None else (_end - 5)

    params = {"sy": _start, "ey": _end}

    # 1. 标猪均价（优先，但仅 2024-2026 有数据）
    rows = db.execute(
        text("""
            SELECT trade_date, value FROM fact_price_daily
            WHERE price_type = '标猪均价' AND region_code = 'NATION' AND source = 'YONGYI'
              AND YEAR(trade_date) BETWEEN :sy AND :ey
            ORDER BY trade_date
        """),
        params,
    ).fetchall()

    have_years = {r[0].year for r in rows} if rows else set()
    wanted_years = set(range(_start, _end + 1))
    missing_years = wanted_years - have_years

    # 2. 缺少年份用全国均价补充（有 2015-2026 完整数据）
    if missing_years:
        fill_rows = []
        for year in sorted(missing_years):
            fill = db.execute(
                text("""
                    SELECT trade_date, value FROM fact_price_daily
                    WHERE price_type = '全国均价' AND region_code = 'NATION' AND source = 'YONGYI'
                      AND YEAR(trade_date) = :y
                    ORDER BY trade_date
                """),
                {"y": year},
            ).fetchall()
            fill_rows.extend(fill)
        rows = list(rows) + fill_rows
        rows = sorted(rows, key=lambda r: r[0])

    # 3. 若仍无数据，用钢联 hog_avg_price
    if not rows:
        rows = db.execute(
            text("""
                SELECT trade_date, value FROM fact_price_daily
                WHERE price_type = 'hog_avg_price' AND region_code = 'NATION' AND source = 'GANGLIAN'
                  AND YEAR(trade_date) BETWEEN :sy AND :ey
                ORDER BY trade_date
            """),
            params,
        ).fetchall()

    series, latest = _rows_to_daily_seasonality(rows)
    return SeasonalityResponse(
        metric_name="全国猪价",
        unit="元/公斤",
        series=series,
        update_time=latest,
        latest_date=latest,
    )


@router.get("/fat-std-spread/seasonality", response_model=SeasonalityResponse)
async def get_fat_std_spread_seasonality(
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    region_code: Optional[str] = Query(None, description="区域代码（可选）"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """标肥价差季节性（全国），NATION 仅钢联有 fat_std_spread"""
    _end = end_year if end_year is not None else date.today().year
    _start = start_year if start_year is not None else (_end - 5)
    rc = region_code or "NATION"
    source_filter = " AND source = 'GANGLIAN'" if rc == "NATION" else ""

    rows = db.execute(
        text(f"""
            SELECT trade_date, value FROM fact_spread_daily
            WHERE spread_type = 'fat_std_spread' AND region_code = :rc {source_filter}
              AND YEAR(trade_date) BETWEEN :sy AND :ey
            ORDER BY trade_date
        """),
        {"rc": rc, "sy": _start, "ey": _end},
    ).fetchall()

    series, latest = _rows_to_daily_seasonality(rows)
    return SeasonalityResponse(
        metric_name="标肥价差",
        unit="元/公斤",
        series=series,
        update_time=latest,
        latest_date=latest,
    )


@router.get("/price-and-spread", response_model=PriceSpreadResponse)
async def get_price_and_spread(
    selected_years: Optional[str] = Query(None, description="选中年份，逗号分隔"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """猪价和标肥价差（可年度筛选），未传年份默认最近 6 年"""
    year_list: List[int] = []
    if selected_years:
        year_list = [int(y.strip()) for y in selected_years.split(",") if y.strip().isdigit()]
    if not year_list:
        _end = date.today().year
        year_list = list(range(_end - 5, _end + 1))

    # 将年份列表转为逗号字符串用于 IN
    year_str = ",".join(str(y) for y in year_list)

    price_rows = db.execute(
        text(f"""
            SELECT trade_date, value FROM fact_price_daily
            WHERE price_type = '标猪均价' AND region_code = 'NATION' AND source = 'YONGYI'
              AND YEAR(trade_date) IN ({year_str})
            ORDER BY trade_date
        """),
    ).fetchall()

    if not price_rows:
        price_rows = db.execute(
            text(f"""
                SELECT trade_date, value FROM fact_price_daily
                WHERE price_type = '全国均价' AND region_code = 'NATION' AND source = 'YONGYI'
                  AND YEAR(trade_date) IN ({year_str})
                ORDER BY trade_date
            """),
        ).fetchall()

    if not price_rows:
        price_rows = db.execute(
            text(f"""
                SELECT trade_date, value FROM fact_price_daily
                WHERE price_type = 'hog_avg_price' AND region_code = 'NATION' AND source = 'GANGLIAN'
                  AND YEAR(trade_date) IN ({year_str})
                ORDER BY trade_date
            """),
        ).fetchall()

    spread_rows = db.execute(
        text(f"""
            SELECT trade_date, value FROM fact_spread_daily
            WHERE spread_type = 'fat_std_spread' AND region_code = 'NATION' AND source = 'GANGLIAN'
              AND YEAR(trade_date) IN ({year_str})
            ORDER BY trade_date
        """),
    ).fetchall()

    price_data = [
        {"date": r[0].isoformat(), "year": r[0].year, "value": float(r[1]) if r[1] is not None else None}
        for r in price_rows
    ]
    spread_data = [
        {"date": r[0].isoformat(), "year": r[0].year, "value": float(r[1]) if r[1] is not None else None}
        for r in spread_rows
    ]

    all_years = sorted({r[0].year for r in price_rows} | {r[0].year for r in spread_rows})

    update_time = None
    if price_rows:
        update_time = price_rows[-1][0].isoformat()
    elif spread_rows:
        update_time = spread_rows[-1][0].isoformat()

    return PriceSpreadResponse(
        price_data=price_data,
        spread_data=spread_data,
        available_years=all_years,
        update_time=update_time,
    )


@router.get("/slaughter/lunar", response_model=SlaughterLunarResponse)
async def get_slaughter_lunar(
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """日度屠宰量（农历对齐）。农历年按正月初八～腊月二十八的阳历区间取数（如 2024 农历年 = 2024-02-17 ～ 2025-01-27）。"""
    _end = end_year if end_year is not None else date.today().year
    _start = start_year if start_year is not None else (_end - 5)

    # 按农历年定义：正月初八～腊月二十八 的阳历区间查询，避免按公历 YEAR 截断导致缺年末数据
    range_start = None
    range_end = None
    for ly in [_start, _end]:
        dr = get_lunar_year_date_range_la_ba(ly)
        if dr:
            s, e = dr
            if range_start is None or s < range_start:
                range_start = s
            if range_end is None or e > range_end:
                range_end = e
    if range_start is None or range_end is None:
        range_start = date(_start, 1, 1)
        range_end = date(_end, 12, 31)

    rows = db.execute(
        text("""
            SELECT trade_date, volume FROM fact_slaughter_daily
            WHERE region_code = 'NATION' AND source = 'YONGYI'
              AND trade_date >= :range_start AND trade_date <= :range_end
            ORDER BY trade_date
        """),
        {"range_start": range_start, "range_end": range_end},
    ).fetchall()

    if not rows:
        return SlaughterLunarResponse(
            metric_name="日度屠宰量",
            unit="头",
            series=[],
            update_time=None,
            latest_date=None,
        )

    # 按农历年分组
    year_data: Dict[int, List[Dict]] = {}
    for row in rows:
        d, v = row[0], row[1]
        lunar_info = solar_to_lunar(d)
        lunar_day_index = lunar_info.get("lunar_day_index")
        is_leap_month = lunar_info.get("is_leap_month", False)
        lunar_year = lunar_info.get("lunar_year")
        lunar_month = lunar_info.get("lunar_month")
        lunar_day = lunar_info.get("lunar_day")
        if lunar_year is None:
            continue
        if lunar_year not in year_data:
            year_data[lunar_year] = []
        year_data[lunar_year].append({
            "date": d,
            "value": float(v) if v is not None else None,
            "lunar_day_index": lunar_day_index,
            "is_leap_month": is_leap_month,
            "lunar_year": lunar_year,
            "lunar_month": lunar_month,
            "lunar_day": lunar_day,
        })

    # 闰月兜底
    for lunar_year_k in list(year_data.keys()):
        leap_info = get_leap_month_info(lunar_year_k)
        if not leap_info:
            continue
        start_d = leap_info.get("leap_month_start")
        end_d = leap_info.get("leap_month_end")
        if not isinstance(start_d, date) or not isinstance(end_d, date):
            continue
        lm = leap_info.get("leap_month")
        for item in year_data[lunar_year_k]:
            if start_d <= item["date"] <= end_d:
                item["is_leap_month"] = True
                item["lunar_month"] = lm
                if item.get("lunar_day") is None:
                    item["lunar_day"] = (item["date"] - start_d).days + 1

    max_index = 0
    valid_indices: List[int] = []
    for year_data_list in year_data.values():
        for item in year_data_list:
            if item["lunar_day_index"] is not None:
                idx = item["lunar_day_index"]
                if idx > max_index:
                    max_index = idx
                valid_indices.append(idx)
    if max_index == 0:
        max_index = 350

    series: List[SeasonalitySeries] = []
    leap_month_series_map: Dict[Tuple[int, int], List[Dict]] = {}

    for year in sorted(year_data.keys()):
        index_to_value: Dict[int, float] = {}
        leap_month_data: Dict[Tuple[int, int], Dict[int, float]] = {}
        for item in year_data[year]:
            if item["is_leap_month"]:
                lm_raw = item["lunar_month"]
                lm = abs(lm_raw) if isinstance(lm_raw, (int, float)) else (lm_raw or 1)
                key = (item["lunar_year"], lm)
                if key not in leap_month_data:
                    leap_month_data[key] = {}
                leap_index = lm * 30 + item["lunar_day"] if item.get("lunar_day") is not None else None
                if leap_index and item["value"] is not None:
                    leap_month_data[key][leap_index] = item["value"]
            else:
                if item["lunar_day_index"] is not None and item["value"] is not None:
                    index_to_value[item["lunar_day_index"]] = item["value"]

        if len(index_to_value) == 0 and len(leap_month_data) == 0:
            continue
        data_points = [
            SeasonalityDataPoint(
                year=year,
                month_day=str(index),
                value=index_to_value.get(index),
                lunar_day_index=index,
            )
            for index in range(1, max_index + 1)
        ]
        if data_points:
            series.append(SeasonalitySeries(year=year, data=data_points))

        for (ly, lm_val), leap_values in leap_month_data.items():
            key2 = (ly, lm_val)
            if key2 not in leap_month_series_map:
                leap_month_series_map[key2] = []
            try:
                from lunar_python import Lunar
                from datetime import date as date_class
                lunar_normal_month_first = Lunar.fromYmd(ly, lm_val, 1)
                solar_normal_first = lunar_normal_month_first.getSolar()
                solar_normal_date = date_class(
                    solar_normal_first.getYear(),
                    solar_normal_first.getMonth(),
                    solar_normal_first.getDay(),
                )
                normal_first_info = solar_to_lunar(solar_normal_date)
                base_index = normal_first_info.get("lunar_day_index")
                fallback_base = (lm_val - 1) * 30 + 1
                if base_index is None or (lm_val >= 2 and base_index < fallback_base):
                    base_index = fallback_base
            except Exception:
                base_index = (lm_val - 1) * 30 + 1
            for leap_idx, value in sorted(leap_values.items()):
                day_in_month = leap_idx % 30 if leap_idx >= 30 else leap_idx
                if day_in_month == 0:
                    day_in_month = 30
                aligned_index = base_index + day_in_month - 1
                leap_month_series_map[key2].append({"index": aligned_index, "value": value})

    for (lunar_year_val, leap_month_val), leap_data in leap_month_series_map.items():
        if lunar_year_val in year_data:
            leap_data_points = [
                SeasonalityDataPoint(
                    year=lunar_year_val,
                    month_day=str(it["index"]),
                    value=it["value"],
                    lunar_day_index=it["index"],
                )
                for it in sorted(leap_data, key=lambda x: x["index"])
            ]
            if leap_data_points:
                series.append(
                    SeasonalitySeries(
                        year=lunar_year_val,
                        data=leap_data_points,
                        is_leap_month=True,
                        leap_month=leap_month_val,
                    )
                )

    latest_date_str = rows[-1][0].isoformat()
    # X 轴只显示 正月初八～腊月二十八，不出现下一年的正月；用参考农历年的区间长度截断标签
    x_axis_labels: Dict[int, str] = {}
    if valid_indices and year_data:
        sample_lunar_year = list(year_data.keys())[0]
        try:
            from lunar_python import Lunar
            from datetime import date as date_class
            dr = get_lunar_year_date_range_la_ba(sample_lunar_year)
            if dr:
                _start_la_ba, _end_la_ba = dr
                max_label_index = (_end_la_ba - _start_la_ba).days + 1  # 仅 01-08 到 12-28
            else:
                max_label_index = max_index
            lunar_new_year = Lunar.fromYmd(sample_lunar_year, 1, 1)
            solar_new_year = lunar_new_year.getSolar()
            new_year_date = date_class(
                solar_new_year.getYear(),
                solar_new_year.getMonth(),
                solar_new_year.getDay(),
            )
            for idx in range(1, min(max_index, max_label_index) + 1):
                target_date = date_class.fromordinal(new_year_date.toordinal() + idx - 1 + 7)
                li = solar_to_lunar(target_date)
                lm2 = li.get("lunar_month")
                ld2 = li.get("lunar_day")
                if lm2 and ld2:
                    x_axis_labels[idx] = f"{lm2:02d}-{ld2:02d}"
        except Exception:
            pass

    return SlaughterLunarResponse(
        metric_name="日度屠宰量",
        unit="头",
        series=series,
        update_time=latest_date_str,
        latest_date=latest_date_str,
        x_axis_labels=x_axis_labels,
    )


@router.get("/slaughter-price-trend/solar", response_model=SlaughterPriceTrendSolarResponse)
async def get_slaughter_price_trend_solar(
    year: Optional[int] = Query(None, description="农历年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """屠宰&价格走势（阳历日期，正月初八~腊月二十八）"""
    current_yr = date.today().year
    candidate_years = list(range(2019, current_yr + 2))
    year_ranges: Dict[int, Tuple[date, date]] = {}
    for y in candidate_years:
        r = get_lunar_year_date_range_la_ba(y)
        if r:
            year_ranges[y] = r

    available_years: List[int] = []
    for y in sorted(year_ranges.keys(), reverse=True):
        sd, ed = year_ranges[y]
        has_data = db.execute(
            text("""
                SELECT 1 FROM fact_slaughter_daily
                WHERE region_code = 'NATION' AND source = 'YONGYI'
                  AND trade_date BETWEEN :s AND :e
                LIMIT 1
            """),
            {"s": sd, "e": ed},
        ).first()
        if not has_data:
            has_data = db.execute(
                text("""
                    SELECT 1 FROM fact_price_daily
                    WHERE price_type = '标猪均价' AND region_code = 'NATION'
                      AND trade_date BETWEEN :s AND :e
                    LIMIT 1
                """),
                {"s": sd, "e": ed},
            ).first()
        if has_data:
            available_years.append(y)

    if not available_years:
        return SlaughterPriceTrendSolarResponse(
            slaughter_data=[], price_data=[], available_years=[], update_time=None, latest_date=None
        )

    query_year = year if year is not None else available_years[0]
    if query_year not in year_ranges:
        raise HTTPException(status_code=400, detail=f"农历年份 {query_year} 无有效日期范围，可用：{available_years}")

    sd, ed = year_ranges[query_year]

    slaughter_rows = db.execute(
        text("""
            SELECT trade_date, volume FROM fact_slaughter_daily
            WHERE region_code = 'NATION' AND source = 'YONGYI'
              AND trade_date BETWEEN :s AND :e
            ORDER BY trade_date
        """),
        {"s": sd, "e": ed},
    ).fetchall()

    price_rows = db.execute(
        text("""
            SELECT trade_date, value FROM fact_price_daily
            WHERE price_type = '标猪均价' AND region_code = 'NATION' AND source = 'YONGYI'
              AND trade_date BETWEEN :s AND :e
            ORDER BY trade_date
        """),
        {"s": sd, "e": ed},
    ).fetchall()
    if not price_rows:
        price_rows = db.execute(
            text("""
                SELECT trade_date, value FROM fact_price_daily
                WHERE price_type = '全国均价' AND region_code = 'NATION' AND source = 'YONGYI'
                  AND trade_date BETWEEN :s AND :e
                ORDER BY trade_date
            """),
            {"s": sd, "e": ed},
        ).fetchall()
    if not price_rows:
        price_rows = db.execute(
            text("""
                SELECT trade_date, value FROM fact_price_daily
                WHERE price_type = 'hog_avg_price' AND region_code = 'NATION' AND source = 'GANGLIAN'
                  AND trade_date BETWEEN :s AND :e
                ORDER BY trade_date
            """),
            {"s": sd, "e": ed},
        ).fetchall()

    slaughter_data = [
        {"date": r[0].isoformat(), "value": float(r[1]) if r[1] is not None else None}
        for r in slaughter_rows
    ]
    price_data = [
        {"date": r[0].isoformat(), "value": float(r[1]) if r[1] is not None else None}
        for r in price_rows
    ]

    latest = slaughter_rows[-1][0].isoformat() if slaughter_rows else (price_rows[-1][0].isoformat() if price_rows else None)

    return SlaughterPriceTrendSolarResponse(
        slaughter_data=slaughter_data,
        price_data=price_data,
        available_years=available_years,
        start_date=sd.isoformat(),
        end_date=ed.isoformat(),
        update_time=latest,
        latest_date=latest,
    )


@router.get("/price-changes")
async def get_price_changes(
    metric_type: str = Query(..., description="指标类型：price 或 spread"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """价格/价差的涨跌数据（5 日 / 10 日 / 30 日、同比）"""
    if metric_type == "price":
        table = "fact_price_daily"
        type_col = "price_type"
        type_val = "标猪均价"
        extra = " AND source = 'YONGYI'"
    else:
        table = "fact_spread_daily"
        type_col = "spread_type"
        type_val = "fat_std_spread"
        extra = " AND source = 'GANGLIAN'"  # NATION 标肥价差仅钢联

    latest_row = db.execute(
        text(f"""
            SELECT trade_date, value FROM {table}
            WHERE {type_col} = :tv AND region_code = 'NATION' {extra}
            ORDER BY trade_date DESC LIMIT 1
        """),
        {"tv": type_val},
    ).first()

    if not latest_row:
        return {
            "current_value": None,
            "latest_date": None,
            "day5_change": None,
            "day10_change": None,
            "day30_change": None,
            "yoy_change": None,
            "unit": "元/公斤",
        }

    latest_date = latest_row[0]
    latest_value = float(latest_row[1]) if latest_row[1] is not None else None

    def _find(target_date):
        r = db.execute(
            text(f"""
                SELECT value FROM {table}
                WHERE {type_col} = :tv AND region_code = 'NATION' {extra}
                  AND trade_date = :td LIMIT 1
            """),
            {"tv": type_val, "td": target_date},
        ).first()
        return float(r[0]) if r and r[0] is not None else None

    d5 = _find(date.fromordinal(latest_date.toordinal() - 5))
    d10 = _find(date.fromordinal(latest_date.toordinal() - 10))
    d30 = _find(date.fromordinal(latest_date.toordinal() - 30))
    try:
        yoy_date = date(latest_date.year - 1, latest_date.month, latest_date.day)
    except ValueError:
        yoy_date = date(latest_date.year - 1, latest_date.month, latest_date.day - 1)
    yoy = _find(yoy_date)

    def _diff(a, b):
        return (a - b) if a is not None and b is not None else None

    return {
        "current_value": latest_value,
        "latest_date": latest_date.isoformat(),
        "day5_change": _diff(latest_value, d5),
        "day10_change": _diff(latest_value, d10),
        "day30_change": _diff(latest_value, d30),
        "yoy_change": _diff(latest_value, yoy),
        "unit": "元/公斤",
    }
