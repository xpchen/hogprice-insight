"""
Observation 兼容层 API - 将旧的 FactObservation 查询映射到 hogprice_v3 fact 表

保留原有接口路径 /api/v1/observation 和响应格式，
底层查询改为直接访问 fact_price_daily / fact_weekly_indicator 等结构化表。
"""
from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys_user import SysUser

router = APIRouter(prefix="/api/v1/observation", tags=["observation"])


class ObservationResponse(BaseModel):
    id: int
    metric_name: str
    obs_date: Optional[date]
    period_type: Optional[str]
    period_start: Optional[date]
    period_end: Optional[date]
    value: Optional[float]
    raw_value: Optional[str]
    geo_code: Optional[str]
    tags: Dict[str, Any]
    unit: Optional[str]

    class Config:
        from_attributes = True


class TagInfo(BaseModel):
    tag_key: str
    tag_value: str
    count: int


# ── metric_key → (table, date_col, filter_col, filter_val, region_mode) ──
# region_mode:
#   "region"       = filter by region_code (NATION or province)
#   "fixed_nation" = always use NATION
#   "avg_provinces" = compute AVG across provinces (no NATION row exists)
_METRIC_ROUTING: Dict[str, tuple] = {
    # 涌益日度价格
    "YY_D_PRICE_NATION_AVG": ("fact_price_daily", "trade_date", "price_type", "标猪均价", "region"),
    "YY_D_SLAUGHTER_TOTAL_1": ("fact_slaughter_daily", "trade_date", None, None, "region"),
    "YY_D_SLAUGHTER_TOTAL_2": ("fact_slaughter_daily", "trade_date", None, None, "region"),
    # 涌益周度
    "YY_W_OUT_PRICE": ("fact_weekly_indicator", "week_end", "indicator_code", "hog_price_out", "region"),
    "YY_W_FROZEN_RATE": ("fact_weekly_indicator", "week_end", "indicator_code", "frozen_rate", "region"),
    "YY_W_PIGLET_PRICE": ("fact_weekly_indicator", "week_end", "indicator_code", "piglet_price_15kg", "region"),
    "YY_W_SOW_PRICE": ("fact_weekly_indicator", "week_end", "indicator_code", "sow_price_50kg", "region"),
    # 涌益均重 - 集团/散户
    "YY_W_WEIGHT_GROUP": ("fact_weekly_indicator", "week_end", "indicator_code", "weight_group", "fixed_nation"),
    "YY_W_WEIGHT_SCATTER": ("fact_weekly_indicator", "week_end", "indicator_code", "weight_scatter", "fixed_nation"),
    # 涌益宰前均重 - province-level only, compute average
    "YY_W_SLAUGHTER_PRELIVE_WEIGHT": ("fact_weekly_indicator", "week_end", "indicator_code", "weight_slaughter", "avg_provinces"),
    # 涌益标肥价差
    "YY_D_STD_FAT_SPREAD": ("fact_spread_daily", "trade_date", "spread_type", "fat_std_spread", "region"),
    # 钢联
    "GL_D_HOG_PRICE": ("fact_price_daily", "trade_date", "price_type", "hog_price", "region"),
    "GL_W_PROFIT": ("fact_weekly_indicator", "week_end", "indicator_code", "profit_breeding_10000", "fixed_nation"),
}

# YY_W_OUT_WEIGHT 根据 indicator 参数路由到不同的 indicator_code
_OUT_WEIGHT_SUBROUTE: Dict[Optional[str], tuple] = {
    "均重":         ("weight_avg", "公斤", "region"),
    "90Kg出栏占比":  ("weight_pct_under90", "", "avg_provinces"),
    "150Kg出栏占重": ("weight_pct_over150", "", "avg_provinces"),
    None:           ("weight_avg", "公斤", "region"),  # default
}


@router.get("/query", response_model=List[ObservationResponse])
async def query_observations(
    source_code: Optional[str] = Query(None, description="数据源代码"),
    metric_key: Optional[str] = Query(None, description="指标键"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    period_type: Optional[str] = Query(None, description="周期类型"),
    geo_code: Optional[str] = Query(None, description="地理位置代码"),
    tag_key: Optional[str] = Query(None, description="Tag键"),
    tag_value: Optional[str] = Query(None, description="Tag值"),
    indicator: Optional[str] = Query(None, description="指标名称"),
    nation_col: Optional[str] = Query(None, description="全国列名"),
    limit: int = Query(1000, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """兼容旧 observation 查询接口"""
    results: list[ObservationResponse] = []

    # ── 特殊处理 YY_W_OUT_WEIGHT：根据 indicator 参数路由到不同指标 ──
    if metric_key == "YY_W_OUT_WEIGHT":
        sub = _OUT_WEIGHT_SUBROUTE.get(indicator, _OUT_WEIGHT_SUBROUTE[None])
        filter_val, unit_override, sub_region_mode = sub
        table = "fact_weekly_indicator"
        date_col = "week_end"
        filter_col = "indicator_code"
        region_mode = sub_region_mode
    else:
        # 尝试路由到新表
        routing = _METRIC_ROUTING.get(metric_key) if metric_key else None
        if routing:
            table, date_col, filter_col, filter_val, region_mode = routing
            unit_override = None
        else:
            table = None

    if table:
        region = "NATION"
        if region_mode == "region" and geo_code and geo_code != "NATION":
            region = geo_code

        # fact_slaughter_daily 特殊处理：用 volume 列, 无 filter 列
        is_slaughter = (table == "fact_slaughter_daily")
        value_col = "volume" if is_slaughter else "value"
        unit_literal = "'头'" if is_slaughter else "unit"

        # 出栏均重(weight_avg)全国：NATION 仅 2024-2026，缺少年份用各省平均补充（省均有 2018-2026）
        is_weight_avg_nation = (
            metric_key == "YY_W_OUT_WEIGHT"
            and filter_val == "weight_avg"
            and region == "NATION"
            and (not source_code or source_code == "YONGYI")
        )

        if region_mode == "avg_provinces":
            # 聚合查询：计算各省平均值作为全国数据
            sql = (
                f"SELECT `{date_col}`, ROUND(AVG({value_col}), 2) as value, "
                f"MIN({unit_literal}) as unit, 'NATION' as region_code "
                f"FROM `{table}` WHERE 1=1 "
                f"AND region_code != 'NATION'"
            )
        else:
            sql = f"SELECT `{date_col}`, {value_col}, {unit_literal}, region_code FROM `{table}` WHERE 1=1"

        params: dict = {}
        if filter_col and filter_val:
            sql += f" AND `{filter_col}` = :fval"
            params["fval"] = filter_val

        if region_mode == "region":
            sql += " AND region_code = :region"
            params["region"] = region
        elif region_mode == "fixed_nation":
            sql += " AND region_code = 'NATION'"

        if start_date:
            sql += f" AND `{date_col}` >= :start"
            params["start"] = start_date
        if end_date:
            sql += f" AND `{date_col}` <= :end"
            params["end"] = end_date

        # source filter: 明确指定时用用户值； slaughter 全国默认 YONGYI； spread fat_std 全国默认 GANGLIAN
        default_src = None
        if not source_code:
            if is_slaughter and region == "NATION":
                default_src = "YONGYI"
            elif table == "fact_spread_daily" and filter_val == "fat_std_spread" and region == "NATION":
                default_src = "GANGLIAN"
        if source_code:
            src_map = {"YONGYI": "YONGYI", "GANGLIAN": "GANGLIAN", "DCE": "DCE"}
            mapped = src_map.get(source_code, source_code)
            sql += " AND source = :src"
            params["src"] = mapped
        elif default_src:
            sql += " AND source = :src"
            params["src"] = default_src

        if region_mode == "avg_provinces":
            sql += f" GROUP BY `{date_col}`"

        sql += f" ORDER BY `{date_col}` DESC LIMIT :lim OFFSET :off"
        params["lim"] = limit
        params["off"] = offset

        rows = db.execute(text(sql), params).fetchall()

        # 出栏均重全国：NATION 仅 2024-2026，缺少年份用各省平均补充
        if is_weight_avg_nation and (start_date or end_date):
            have_weeks = {r[0] for r in rows}
            fill_sql = (
                f"SELECT `{date_col}`, ROUND(AVG({value_col}), 2) as value, "
                f"MIN({unit_literal}) as unit, 'NATION' as region_code "
                f"FROM `{table}` WHERE indicator_code = :fval AND region_code != 'NATION' "
                f"AND source = 'YONGYI'"
            )
            fill_params: dict = {"fval": filter_val}
            if start_date:
                fill_sql += f" AND `{date_col}` >= :start"
                fill_params["start"] = start_date
            if end_date:
                fill_sql += f" AND `{date_col}` <= :end"
                fill_params["end"] = end_date
            fill_sql += f" GROUP BY `{date_col}` ORDER BY `{date_col}` DESC"
            fill_rows = db.execute(text(fill_sql), fill_params).fetchall()
            for r in fill_rows:
                if r[0] not in have_weeks:
                    rows = list(rows) + [r]
                    have_weeks.add(r[0])
            rows = sorted(rows, key=lambda x: x[0], reverse=True)
            rows = rows[offset : offset + limit]

        for i, r in enumerate(rows):
            period = "day"
            if "weekly" in table:
                period = "week"
            elif "monthly" in table:
                period = "month"

            results.append(ObservationResponse(
                id=i + 1,
                metric_name=metric_key or filter_val,
                obs_date=r[0],
                period_type=period,
                period_start=r[0],
                period_end=r[0],
                value=float(r[1]) if r[1] is not None else None,
                raw_value=str(r[1]) if r[1] is not None else None,
                geo_code=r[3] if r[3] else None,
                tags={"source": source_code or "", "indicator": indicator or ""},
                unit=r[2]
            ))

    else:
        # 无路由匹配：尝试在 fact_weekly_indicator 按 indicator_code 搜索
        if metric_key:
            sql = "SELECT week_end, value, unit, region_code FROM fact_weekly_indicator WHERE indicator_code = :code"
            params = {"code": metric_key}
            if geo_code and geo_code != "NATION":
                sql += " AND region_code = :region"
                params["region"] = geo_code
            if start_date:
                sql += " AND week_end >= :start"
                params["start"] = start_date
            if end_date:
                sql += " AND week_end <= :end"
                params["end"] = end_date
            sql += " ORDER BY week_end DESC LIMIT :lim OFFSET :off"
            params["lim"] = limit
            params["off"] = offset
            rows = db.execute(text(sql), params).fetchall()
            for i, r in enumerate(rows):
                results.append(ObservationResponse(
                    id=i + 1, metric_name=metric_key, obs_date=r[0],
                    period_type="week", period_start=r[0], period_end=r[0],
                    value=float(r[1]) if r[1] is not None else None,
                    raw_value=str(r[1]) if r[1] is not None else None,
                    geo_code=r[3], tags={}, unit=r[2]
                ))

    return results


@router.get("/tags", response_model=List[TagInfo])
async def get_available_tags(
    tag_key: Optional[str] = Query(None, description="Tag键"),
    source_code: Optional[str] = Query(None, description="数据源代码"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """返回可用的标签（从新表动态提取）"""
    tags: list[TagInfo] = []

    if tag_key == "source":
        for src in ["YONGYI", "GANGLIAN", "NBS"]:
            tags.append(TagInfo(tag_key="source", tag_value=src, count=0))
    elif tag_key == "region":
        rows = db.execute(text("SELECT region_code, region_name FROM dim_region ORDER BY region_code")).fetchall()
        for r in rows:
            tags.append(TagInfo(tag_key="region", tag_value=r[0], count=0))
    elif tag_key == "indicator":
        rows = db.execute(text(
            "SELECT DISTINCT indicator_code FROM fact_weekly_indicator ORDER BY indicator_code LIMIT 100"
        )).fetchall()
        for r in rows:
            tags.append(TagInfo(tag_key="indicator", tag_value=r[0], count=0))
    else:
        for k in ["source", "region", "indicator"]:
            tags.append(TagInfo(tag_key=k, tag_value="", count=0))

    return tags


@router.get("/raw/sheets")
async def get_raw_sheets(
    batch_id: Optional[int] = Query(None, description="批次ID"),
    raw_file_id: Optional[int] = Query(None, description="Raw文件ID"),
    parse_status: Optional[str] = Query(None, description="解析状态"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取导入批次信息（兼容旧接口）"""
    rows = db.execute(text(
        "SELECT id, batch_mode, source_dir, started_at, finished_at, total_rows, file_count "
        "FROM import_batch ORDER BY id DESC LIMIT 50"
    )).fetchall()
    return [
        {
            "id": r[0],
            "raw_file_id": r[0],
            "sheet_name": r[1] or "bulk",
            "row_count": r[5],
            "col_count": r[6],
            "parse_status": "done" if r[4] else "pending",
            "parser_type": "import_tool",
            "error_count": 0,
            "observation_count": r[5] or 0
        }
        for r in rows
    ]


@router.get("/raw/table")
async def get_raw_table(
    raw_sheet_id: int = Query(..., description="批次 ID"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取批次详情（兼容旧接口）"""
    row = db.execute(text(
        "SELECT id, batch_mode, source_dir, started_at, finished_at, total_rows "
        "FROM import_batch WHERE id = :bid"
    ), {"bid": raw_sheet_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {
        "raw_sheet_id": row[0],
        "table_json": {"batch_mode": row[1], "source_dir": row[2], "total_rows": row[5]},
        "merged_cells_json": None,
        "created_at": row[3].isoformat() if row[3] else None
    }
