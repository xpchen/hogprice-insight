"""
A1. 价格（全国） 专用 API
拆分为独立模块，包含：全国猪价季节性、标肥价差季节性、猪价&标肥价差、日度屠宰量（农历）、价格/价差涨跌
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, load_only
from sqlalchemy import func, or_, extract
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys_user import SysUser
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.services.lunar_alignment_service import solar_to_lunar, get_lunar_year_date_range_la_ba

# 复用 price_display 的响应模型，避免重复定义
from app.api.price_display import (
    SeasonalityDataPoint,
    SeasonalitySeries,
    SeasonalityResponse,
    PriceSpreadResponse,
    SlaughterLunarResponse,
)

router = APIRouter(tags=["price-national"])


class SlaughterPriceTrendSolarResponse(BaseModel):
    """屠宰&价格 相关走势（按年，阳历日期 正月初八～腊月二十八）"""
    slaughter_data: List[Dict[str, Any]]
    price_data: List[Dict[str, Any]]
    available_years: List[int]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


@router.get("/national-price/seasonality", response_model=SeasonalityResponse)
async def get_national_price_seasonality(
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取全国猪价季节性数据。返回按年份对齐的季节性数据。"""
    metric = db.query(DimMetric).filter(
        or_(
            DimMetric.raw_header.like("%中国%"),
            DimMetric.raw_header.like("%全国%"),
        ),
        DimMetric.sheet_name == "分省区猪价",
        DimMetric.freq.in_(["D", "daily", "D"]),
    ).first()
    if not metric:
        metric = db.query(DimMetric).filter(
            DimMetric.metric_name.like("%全国%"),
            DimMetric.metric_name.like("%价格%"),
            DimMetric.freq.in_(["D", "daily", "D"]),
        ).first()
    if not metric:
        metric = db.query(DimMetric).filter(
            DimMetric.raw_header.like("%中国%"),
            DimMetric.sheet_name == "分省区猪价",
        ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="未找到全国猪价指标")

    _end = end_year if end_year is not None else date.today().year
    _start = start_year if start_year is not None else (_end - 5)
    query = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.period_type == "day",
    )
    query = query.filter(extract("year", FactObservation.obs_date) >= _start)
    query = query.filter(extract("year", FactObservation.obs_date) <= _end)
    query = query.options(load_only(FactObservation.obs_date, FactObservation.value))
    observations = query.order_by(FactObservation.obs_date).all()

    if not observations:
        return SeasonalityResponse(
            metric_name=metric.metric_name,
            unit=metric.unit or "元/公斤",
            series=[],
            update_time=None,
            latest_date=None,
        )

    year_data: Dict[int, List[Dict]] = {}
    for obs in observations:
        year = obs.obs_date.year
        if year not in year_data:
            year_data[year] = []
        month_day = obs.obs_date.strftime("%m-%d")
        year_data[year].append({
            "month_day": month_day,
            "value": float(obs.value) if obs.value else None,
            "date": obs.obs_date,
        })

    series = []
    for year in sorted(year_data.keys()):
        data_points = [
            SeasonalityDataPoint(year=year, month_day=item["month_day"], value=item["value"])
            for item in sorted(year_data[year], key=lambda x: x["date"])
        ]
        series.append(SeasonalitySeries(year=year, data=data_points))

    latest_obs = observations[-1]
    update_time = latest_obs.obs_date.isoformat()
    return SeasonalityResponse(
        metric_name=metric.metric_name,
        unit=metric.unit or "元/公斤",
        series=series,
        update_time=update_time,
        latest_date=update_time,
    )


@router.get("/fat-std-spread/seasonality", response_model=SeasonalityResponse)
async def get_fat_std_spread_seasonality(
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    region_code: Optional[str] = Query(None, description="区域代码（可选）"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取标肥价差季节性数据（全国）。返回按年份对齐的季节性数据。"""
    metric = db.query(DimMetric).filter(
        DimMetric.raw_header.like("%中国%"),
        DimMetric.sheet_name == "肥标价差",
    ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="未找到标肥价差指标（中国列）")

    _end = end_year if end_year is not None else date.today().year
    _start = start_year if start_year is not None else (_end - 5)
    query = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.period_type == "day",
    )
    query = query.filter(
        func.json_unquote(func.json_extract(FactObservation.tags_json, "$.scope")) == "nation"
    )
    query = query.filter(extract("year", FactObservation.obs_date) >= _start)
    query = query.filter(extract("year", FactObservation.obs_date) <= _end)
    query = query.options(load_only(FactObservation.obs_date, FactObservation.value))
    observations = query.order_by(FactObservation.obs_date).all()

    if not observations:
        return SeasonalityResponse(
            metric_name=metric.metric_name,
            unit=metric.unit or "元/公斤",
            series=[],
            update_time=None,
            latest_date=None,
        )

    year_data: Dict[int, List[Dict]] = {}
    for obs in observations:
        year = obs.obs_date.year
        if year not in year_data:
            year_data[year] = []
        month_day = obs.obs_date.strftime("%m-%d")
        year_data[year].append({
            "month_day": month_day,
            "value": float(obs.value) if obs.value else None,
            "date": obs.obs_date,
        })

    series = []
    for year in sorted(year_data.keys()):
        data_points = [
            SeasonalityDataPoint(year=year, month_day=item["month_day"], value=item["value"])
            for item in sorted(year_data[year], key=lambda x: x["date"])
        ]
        series.append(SeasonalitySeries(year=year, data=data_points))

    latest_obs = observations[-1]
    update_time = latest_obs.obs_date.isoformat()
    return SeasonalityResponse(
        metric_name=metric.metric_name,
        unit=metric.unit or "元/公斤",
        series=series,
        update_time=update_time,
        latest_date=update_time,
    )


@router.get("/price-and-spread", response_model=PriceSpreadResponse)
async def get_price_and_spread(
    selected_years: Optional[str] = Query(None, description="选中的年份，逗号分隔"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取猪价和标肥价差数据（可年度筛选）。未传年份时默认最近6年。"""
    year_list: List[int] = []
    if selected_years:
        year_list = [int(y.strip()) for y in selected_years.split(",") if y.strip().isdigit()]
    if not year_list:
        _end = date.today().year
        year_list = list(range(_end - 5, _end + 1))

    price_metric = db.query(DimMetric).filter(
        DimMetric.raw_header.like("%中国%"),
        DimMetric.sheet_name == "分省区猪价",
    ).first()
    spread_metric = db.query(DimMetric).filter(
        DimMetric.raw_header.like("%中国%"),
        DimMetric.sheet_name == "肥标价差",
    ).first()
    if not price_metric or not spread_metric:
        raise HTTPException(status_code=404, detail="未找到价格或价差指标")

    price_query = db.query(FactObservation).filter(
        FactObservation.metric_id == price_metric.id,
        FactObservation.period_type == "day",
    )
    price_query = price_query.filter(extract("year", FactObservation.obs_date).in_(year_list))
    price_query = price_query.options(load_only(FactObservation.obs_date, FactObservation.value))
    price_obs = price_query.order_by(FactObservation.obs_date).all()

    spread_query = db.query(FactObservation).filter(
        FactObservation.metric_id == spread_metric.id,
        FactObservation.period_type == "day",
    )
    spread_query = spread_query.filter(
        func.json_unquote(func.json_extract(FactObservation.tags_json, "$.scope")) == "nation"
    )
    spread_query = spread_query.filter(extract("year", FactObservation.obs_date).in_(year_list))
    spread_query = spread_query.options(load_only(FactObservation.obs_date, FactObservation.value))
    spread_obs = spread_query.order_by(FactObservation.obs_date).all()

    all_years = set(o.obs_date.year for o in price_obs + spread_obs)
    available_years = sorted(all_years)
    price_data = [
        {"date": o.obs_date.isoformat(), "year": o.obs_date.year, "value": float(o.value) if o.value else None}
        for o in price_obs
    ]
    spread_data = [
        {"date": o.obs_date.isoformat(), "year": o.obs_date.year, "value": float(o.value) if o.value else None}
        for o in spread_obs
    ]
    latest_date = None
    if price_obs:
        latest_date = price_obs[-1].obs_date.isoformat()
    elif spread_obs:
        latest_date = spread_obs[-1].obs_date.isoformat()
    return PriceSpreadResponse(
        price_data=price_data,
        spread_data=spread_data,
        available_years=available_years,
        update_time=latest_date,
    )


@router.get("/slaughter/lunar", response_model=SlaughterLunarResponse)
async def get_slaughter_lunar(
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取日度屠宰量数据（农历对齐）。未传年份时默认最近6年。"""
    metric = db.query(DimMetric).filter(
        func.json_extract(DimMetric.parse_json, "$.metric_key") == "YY_D_SLAUGHTER_TOTAL_1",
        DimMetric.sheet_name == "价格+宰量",
        DimMetric.freq == "D",
    ).first()
    if not metric:
        metric = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, "$.metric_key") == "YY_D_SLAUGHTER_TOTAL_2",
            DimMetric.freq == "D",
        ).first()
    if not metric:
        metric = db.query(DimMetric).filter(
            DimMetric.metric_name.like("%屠宰量%"),
            DimMetric.sheet_name == "价格+宰量",
            DimMetric.freq == "D",
        ).first()
    if not metric:
        metric = db.query(DimMetric).filter(
            or_(
                DimMetric.raw_header.like("%屠宰量%"),
                DimMetric.raw_header.like("%宰量%"),
            ),
            DimMetric.sheet_name == "价格+宰量",
            DimMetric.freq == "D",
        ).first()
    if not metric:
        metric = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, "$.metric_key").like("%SLAUGHTER%"),
            DimMetric.freq == "D",
        ).first()
    if not metric:
        metric = db.query(DimMetric).filter(
            DimMetric.raw_header.like("%日度屠宰量%"),
            DimMetric.freq == "D",
        ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="未找到日度屠宰量指标")

    _end = end_year if end_year is not None else date.today().year
    _start = start_year if start_year is not None else (_end - 5)
    query = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.period_type == "day",
    )
    query = query.filter(extract("year", FactObservation.obs_date) >= _start)
    query = query.filter(extract("year", FactObservation.obs_date) <= _end)
    query = query.options(load_only(FactObservation.obs_date, FactObservation.value))
    observations = query.order_by(FactObservation.obs_date).all()

    if not observations:
        return SlaughterLunarResponse(
            metric_name=metric.metric_name,
            unit=metric.unit or "头",
            series=[],
            update_time=None,
            latest_date=None,
        )

    year_data: Dict[int, List[Dict]] = {}
    for obs in observations:
        lunar_info = solar_to_lunar(obs.obs_date)
        lunar_day_index = lunar_info.get("lunar_day_index")
        is_leap_month = lunar_info.get("is_leap_month", False)
        lunar_year = lunar_info.get("lunar_year")
        lunar_month = lunar_info.get("lunar_month")
        lunar_day = lunar_info.get("lunar_day")
        if lunar_year is None:
            continue
        if lunar_year not in year_data:
            year_data[lunar_year] = []
        obs_value = float(obs.value) if obs.value is not None else None
        year_data[lunar_year].append({
            "date": obs.obs_date,
            "value": obs_value,
            "lunar_day_index": lunar_day_index,
            "is_leap_month": is_leap_month,
            "lunar_year": lunar_year,
            "lunar_month": lunar_month,
            "lunar_day": lunar_day,
        })

    max_index = 0
    valid_indices = []
    for year_data_list in year_data.values():
        for item in year_data_list:
            if item["lunar_day_index"] is not None:
                idx = item["lunar_day_index"]
                if idx > max_index:
                    max_index = idx
                valid_indices.append(idx)
    if max_index == 0:
        max_index = 350

    series = []
    leap_month_series_map: Dict[Tuple[int, int], List[Dict]] = {}
    for year in sorted(year_data.keys()):
        index_to_value: Dict[int, float] = {}
        leap_month_data: Dict[Tuple[int, int], Dict[int, float]] = {}
        for item in year_data[year]:
            if item["is_leap_month"]:
                key = (item["lunar_year"], item["lunar_month"])
                if key not in leap_month_data:
                    leap_month_data[key] = {}
                leap_index = item["lunar_month"] * 30 + item["lunar_day"] if item.get("lunar_day") else None
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

        for (ly, lm), leap_values in leap_month_data.items():
            key = (ly, lm)
            if key not in leap_month_series_map:
                leap_month_series_map[key] = []
            try:
                from lunar_python import Lunar
                from datetime import date as date_class
                lunar_normal_month_first = Lunar.fromYmd(ly, lm, 1)
                solar_normal_first = lunar_normal_month_first.getSolar()
                solar_normal_date = date_class(
                    solar_normal_first.getYear(),
                    solar_normal_first.getMonth(),
                    solar_normal_first.getDay(),
                )
                normal_first_info = solar_to_lunar(solar_normal_date)
                base_index = normal_first_info.get("lunar_day_index")
                if base_index is None:
                    base_index = (lm - 1) * 30 + 1
            except Exception:
                base_index = (lm - 1) * 30 + 1
            for leap_index, value in sorted(leap_values.items()):
                day_in_month = leap_index % 30 if leap_index >= 30 else leap_index
                if day_in_month == 0:
                    day_in_month = 30
                aligned_index = base_index + day_in_month - 1
                leap_month_series_map[key].append({"index": aligned_index, "value": value})
    for (lunar_year, leap_month), leap_data in leap_month_series_map.items():
        if lunar_year in year_data:
            leap_data_points = [
                SeasonalityDataPoint(
                    year=lunar_year,
                    month_day=str(item["index"]),
                    value=item["value"],
                    lunar_day_index=item["index"],
                )
                for item in sorted(leap_data, key=lambda x: x["index"])
            ]
            if leap_data_points:
                series.append(
                    SeasonalitySeries(
                        year=lunar_year,
                        data=leap_data_points,
                        is_leap_month=True,
                        leap_month=leap_month,
                    )
                )

    latest_obs = observations[-1]
    update_time = latest_obs.obs_date.isoformat()
    x_axis_labels: Dict[int, str] = {}
    if valid_indices and year_data:
        sample_lunar_year = list(year_data.keys())[0]
        try:
            from lunar_python import Lunar
            from datetime import date as date_class
            lunar_new_year = Lunar.fromYmd(sample_lunar_year, 1, 1)
            solar_new_year = lunar_new_year.getSolar()
            new_year_date = date_class(
                solar_new_year.getYear(),
                solar_new_year.getMonth(),
                solar_new_year.getDay(),
            )
            for idx in range(1, max_index + 1):
                target_date = date_class.fromordinal(new_year_date.toordinal() + idx - 1 + 7)
                lunar_info = solar_to_lunar(target_date)
                lunar_month = lunar_info.get("lunar_month")
                lunar_day = lunar_info.get("lunar_day")
                if lunar_month and lunar_day:
                    x_axis_labels[idx] = f"{lunar_month:02d}-{lunar_day:02d}"
        except Exception:
            pass

    return SlaughterLunarResponse(
        metric_name=metric.metric_name,
        unit=metric.unit or "头",
        series=series,
        update_time=update_time,
        latest_date=update_time,
        x_axis_labels=x_axis_labels,
    )


def _get_slaughter_metric(db: Session) -> DimMetric:
    """获取日度屠宰量指标（价格+宰量 sheet，优先 _1）。"""
    m = db.query(DimMetric).filter(
        func.json_extract(DimMetric.parse_json, "$.metric_key") == "YY_D_SLAUGHTER_TOTAL_1",
        DimMetric.sheet_name == "价格+宰量",
        DimMetric.freq == "D",
    ).first()
    if m:
        return m
    m = db.query(DimMetric).filter(
        func.json_extract(DimMetric.parse_json, "$.metric_key") == "YY_D_SLAUGHTER_TOTAL_2",
        DimMetric.freq == "D",
    ).first()
    if m:
        return m
    m = db.query(DimMetric).filter(
        DimMetric.metric_name.like("%屠宰量%"),
        DimMetric.sheet_name == "价格+宰量",
        DimMetric.freq == "D",
    ).first()
    if m:
        return m
    m = db.query(DimMetric).filter(
        or_(
            DimMetric.raw_header.like("%屠宰量%"),
            DimMetric.raw_header.like("%宰量%"),
        ),
        DimMetric.sheet_name == "价格+宰量",
        DimMetric.freq == "D",
    ).first()
    if m:
        return m
    raise HTTPException(status_code=404, detail="未找到日度屠宰量指标")


def _get_price_metric_price_slaughter_sheet(db: Session) -> DimMetric:
    """获取价格+宰量 sheet 的全国均价指标。"""
    m = db.query(DimMetric).filter(
        func.json_extract(DimMetric.parse_json, "$.metric_key") == "YY_D_PRICE_NATION_AVG",
        DimMetric.sheet_name == "价格+宰量",
        DimMetric.freq == "D",
    ).first()
    if m:
        return m
    m = db.query(DimMetric).filter(
        DimMetric.sheet_name == "价格+宰量",
        or_(
            DimMetric.raw_header.like("%全国均价%"),
            DimMetric.raw_header.like("%全国%"),
            DimMetric.metric_name.like("%全国均价%"),
        ),
        DimMetric.freq == "D",
    ).first()
    if m:
        return m
    raise HTTPException(status_code=404, detail="未找到价格+宰量 sheet 的全国均价指标")


@router.get("/slaughter-price-trend/solar", response_model=SlaughterPriceTrendSolarResponse)
async def get_slaughter_price_trend_solar(
    year: Optional[int] = Query(None, description="农历年份，如 2024；不传则返回可用年份及最近一年数据"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    屠宰&价格 相关走势（按年筛选，阳历日期）。
    数据范围：每年农历正月初八至腊月二十八，用阳历日期对齐展示。
    一般按年度查询，例如单独查询某年的量价走势。
    """
    slaughter_metric = _get_slaughter_metric(db)
    price_metric = _get_price_metric_price_slaughter_sheet(db)

    # 可用农历年：能算出正月初八～腊月二十八，且该区间内确有屠宰量或价格数据
    current = date.today().year
    candidate_years = list(range(2019, current + 2))
    year_ranges: Dict[int, Tuple[date, date]] = {}
    for y in candidate_years:
        r = get_lunar_year_date_range_la_ba(y)
        if r:
            year_ranges[y] = r

    available_years = []
    for y in sorted(year_ranges.keys(), reverse=True):
        start_date, end_date = year_ranges[y]
        has_slaughter = (
            db.query(FactObservation)
            .filter(
                FactObservation.metric_id == slaughter_metric.id,
                FactObservation.period_type == "day",
                FactObservation.obs_date >= start_date,
                FactObservation.obs_date <= end_date,
            )
            .limit(1)
            .first()
            is not None
        )
        has_price = (
            db.query(FactObservation)
            .filter(
                FactObservation.metric_id == price_metric.id,
                FactObservation.period_type == "day",
                FactObservation.obs_date >= start_date,
                FactObservation.obs_date <= end_date,
            )
            .limit(1)
            .first()
            is not None
        )
        if has_slaughter or has_price:
            available_years.append(y)

    if not available_years:
        return SlaughterPriceTrendSolarResponse(
            slaughter_data=[],
            price_data=[],
            available_years=[],
            update_time=None,
            latest_date=None,
        )

    # 若未传 year，默认用最近一个可用年
    query_year = year
    if query_year is None:
        query_year = available_years[0]
    if query_year not in year_ranges:
        raise HTTPException(
            status_code=400,
            detail=f"农历年份 {query_year} 无有效日期范围，可用：{available_years}",
        )

    start_date, end_date = year_ranges[query_year]

    slaughter_query = db.query(FactObservation).filter(
        FactObservation.metric_id == slaughter_metric.id,
        FactObservation.period_type == "day",
        FactObservation.obs_date >= start_date,
        FactObservation.obs_date <= end_date,
    )
    slaughter_query = slaughter_query.options(
        load_only(FactObservation.obs_date, FactObservation.value)
    )
    slaughter_obs = slaughter_query.order_by(FactObservation.obs_date).all()

    price_query = db.query(FactObservation).filter(
        FactObservation.metric_id == price_metric.id,
        FactObservation.period_type == "day",
        FactObservation.obs_date >= start_date,
        FactObservation.obs_date <= end_date,
    )
    price_query = price_query.options(
        load_only(FactObservation.obs_date, FactObservation.value)
    )
    price_obs = price_query.order_by(FactObservation.obs_date).all()

    slaughter_data = [
        {"date": o.obs_date.isoformat(), "value": float(o.value) if o.value is not None else None}
        for o in slaughter_obs
    ]
    price_data = [
        {"date": o.obs_date.isoformat(), "value": float(o.value) if o.value is not None else None}
        for o in price_obs
    ]

    latest_date = None
    if slaughter_obs:
        latest_date = slaughter_obs[-1].obs_date.isoformat()
    elif price_obs:
        latest_date = price_obs[-1].obs_date.isoformat()

    return SlaughterPriceTrendSolarResponse(
        slaughter_data=slaughter_data,
        price_data=price_data,
        available_years=available_years,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        update_time=latest_date,
        latest_date=latest_date,
    )


@router.get("/price-changes")
async def get_price_changes(
    metric_type: str = Query(..., description="指标类型：price 或 spread"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取价格/价差的涨跌数据（5日/10日/30日、同比）。"""
    if metric_type == "price":
        metric = db.query(DimMetric).filter(
            DimMetric.raw_header.like("%中国%"),
            DimMetric.sheet_name == "分省区猪价",
        ).first()
    else:
        metric = db.query(DimMetric).filter(
            DimMetric.raw_header.like("%中国%"),
            DimMetric.sheet_name == "肥标价差",
        ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="未找到指标")

    latest_obs = (
        db.query(FactObservation)
        .filter(FactObservation.metric_id == metric.id)
        .order_by(FactObservation.obs_date.desc())
        .first()
    )
    if not latest_obs:
        return {
            "current_value": None,
            "latest_date": None,
            "day5_change": None,
            "day10_change": None,
            "day30_change": None,
            "yoy_change": None,
            "unit": metric.unit or "元/公斤",
        }

    latest_date = latest_obs.obs_date
    latest_value = float(latest_obs.value) if latest_obs.value else None
    day5_date = date.fromordinal(latest_date.toordinal() - 5)
    day10_date = date.fromordinal(latest_date.toordinal() - 10)
    day30_date = date.fromordinal(latest_date.toordinal() - 30)
    last_year_date = date(latest_date.year - 1, latest_date.month, latest_date.day)

    day5_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == day5_date,
    ).first()
    day10_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == day10_date,
    ).first()
    day30_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == day30_date,
    ).first()
    yoy_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == last_year_date,
    ).first()

    day5_change = latest_value - float(day5_obs.value) if (latest_value is not None and day5_obs and day5_obs.value) else None
    day10_change = latest_value - float(day10_obs.value) if (latest_value is not None and day10_obs and day10_obs.value) else None
    day30_change = latest_value - float(day30_obs.value) if (latest_value is not None and day30_obs and day30_obs.value) else None
    yoy_change = latest_value - float(yoy_obs.value) if (latest_value is not None and yoy_obs and yoy_obs.value) else None

    return {
        "current_value": latest_value,
        "latest_date": latest_date.isoformat(),
        "day5_change": day5_change,
        "day10_change": day10_change,
        "day30_change": day30_change,
        "yoy_change": yoy_change,
        "unit": metric.unit or "元/公斤",
    }
