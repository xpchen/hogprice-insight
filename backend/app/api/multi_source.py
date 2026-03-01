"""
E2. 多渠道汇总 API
包含3个表格：
1. 淘汰母猪屠宰环比、能繁母猪存栏环比、能繁母猪饲料环比
2. 新生仔猪存栏环比、仔猪饲料环比
3. 生猪存栏环比、育肥猪饲料环比

数据来源：fact_monthly_indicator 表（hogprice_v3 数据库）
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db

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
    breeding_inventory_nyb: Optional[float] = None  # 能繁母猪存栏环比-NYB（全国，兼容旧字段）
    breeding_inventory_nyb_nation: Optional[float] = None  # 能繁-NYB-全国
    breeding_inventory_nyb_scale: Optional[float] = None  # 能繁-NYB-规模场
    breeding_inventory_nyb_small: Optional[float] = None  # 能繁-NYB-散户
    breeding_feed_yongyi: Optional[float] = None  # 能繁母猪饲料环比-涌益
    breeding_feed_ganglian: Optional[float] = None  # 能繁母猪饲料环比-钢联
    breeding_feed_association: Optional[float] = None  # 能繁母猪饲料环比-协会
    piglet_inventory_yongyi: Optional[float] = None  # 新生仔猪存栏环比-涌益
    piglet_inventory_ganglian_nation: Optional[float] = None  # 新生仔猪存栏环比-钢联-全国
    piglet_inventory_ganglian_scale: Optional[float] = None  # 新生仔猪存栏环比-钢联-规模场
    piglet_inventory_ganglian_small: Optional[float] = None  # 新生仔猪存栏环比-钢联-中小散户
    piglet_inventory_nyb: Optional[float] = None  # 新生仔猪存栏环比-NYB（全国，兼容）
    piglet_inventory_nyb_nation: Optional[float] = None  # 新生仔猪-NYB-全国
    piglet_inventory_nyb_scale: Optional[float] = None  # 新生仔猪-NYB-规模场
    piglet_inventory_nyb_small: Optional[float] = None  # 新生仔猪-NYB-散户
    piglet_feed_yongyi: Optional[float] = None  # 仔猪饲料环比-涌益
    piglet_feed_ganglian: Optional[float] = None  # 仔猪饲料环比-钢联
    piglet_feed_association: Optional[float] = None  # 仔猪饲料环比-协会
    hog_inventory_yongyi: Optional[float] = None  # 生猪存栏环比-涌益
    hog_inventory_ganglian_nation: Optional[float] = None  # 生猪存栏环比-钢联-全国
    hog_inventory_ganglian_scale: Optional[float] = None  # 生猪存栏环比-钢联-规模场
    hog_inventory_ganglian_small: Optional[float] = None  # 生猪存栏环比-钢联-中小散户
    hog_inventory_nyb: Optional[float] = None  # 生猪存栏环比-NYB（全国，兼容）
    hog_inventory_nyb_nation: Optional[float] = None  # 生猪存栏-NYB-全国
    hog_inventory_nyb_scale: Optional[float] = None  # 生猪存栏-NYB-规模场
    hog_inventory_nyb_small: Optional[float] = None  # 生猪存栏-NYB-散户
    hog_inventory_nyb_5month: Optional[float] = None  # 生猪存栏环比-NYB-5月龄
    hog_feed_yongyi: Optional[float] = None  # 育肥猪饲料环比-涌益
    hog_feed_ganglian: Optional[float] = None  # 育肥猪饲料环比-钢联
    hog_feed_association: Optional[float] = None  # 育肥猪饲料环比-协会


class MultiSourceResponse(BaseModel):
    """多渠道汇总响应"""
    data: List[MultiSourceDataPoint]
    latest_month: Optional[str] = None


# ---------------------------------------------------------------------------
# Mapping: (indicator_code, source, sub_category, region_code) -> response field
#
# All values queried from fact_monthly_indicator for this API use
# value_type = 'mom_pct' (month-over-month percentage).
# sub_category and region_code use NULL / 'NATION' as defaults; we
# normalise NULLs via COALESCE in the SQL query.
# ---------------------------------------------------------------------------
INDICATOR_FIELD_MAP: dict[tuple[str, str, str, str], str] = {
    # --- 淘汰母猪屠宰环比 ---
    ("cull_slaughter", "YONGYI", "", "NATION"): "cull_slaughter_yongyi",
    ("cull_slaughter", "GANGLIAN", "", "NATION"): "cull_slaughter_ganglian",

    # --- 能繁母猪存栏环比 ---
    ("breeding_sow_inventory", "YONGYI", "", "NATION"): "breeding_inventory_yongyi",
    # 钢联: nation=全国, small_nation=中小散户
    ("breeding_sow_inventory", "GANGLIAN", "nation", "NATION"): "breeding_inventory_ganglian_nation",
    ("breeding_sow_inventory", "GANGLIAN", "small_nation", "NATION"): "breeding_inventory_ganglian_small",
    # NYB: nation/scale/small
    ("breeding_sow_inventory", "NYB", "nation", "NATION"): "breeding_inventory_nyb_nation",
    ("breeding_sow_inventory", "NYB", "scale", "NATION"): "breeding_inventory_nyb_scale",
    ("breeding_sow_inventory", "NYB", "small", "NATION"): "breeding_inventory_nyb_small",

    # --- 能繁母猪饲料环比 ---
    # YONGYI sub_cats: other/production_mom/reserve — fallback to empty matches any
    ("breeding_sow_feed", "YONGYI", "", "NATION"): "breeding_feed_yongyi",
    ("breeding_sow_feed", "GANGLIAN", "nation", "NATION"): "breeding_feed_ganglian",
    ("breeding_sow_feed", "ASSOCIATION", "", "NATION"): "breeding_feed_association",

    # --- 新生仔猪存栏环比 ---
    ("piglet_inventory", "YONGYI", "", "NATION"): "piglet_inventory_yongyi",
    ("piglet_inventory", "GANGLIAN", "nation", "NATION"): "piglet_inventory_ganglian_nation",
    ("piglet_inventory", "GANGLIAN", "small_nation", "NATION"): "piglet_inventory_ganglian_small",
    ("piglet_inventory", "NYB", "nation", "NATION"): "piglet_inventory_nyb_nation",
    ("piglet_inventory", "NYB", "scale", "NATION"): "piglet_inventory_nyb_scale",
    ("piglet_inventory", "NYB", "small", "NATION"): "piglet_inventory_nyb_small",

    # --- 仔猪饲料环比 ---
    # YONGYI sub_cats: nursery/production_mom/small — fallback to empty matches any
    ("piglet_feed", "YONGYI", "", "NATION"): "piglet_feed_yongyi",
    ("piglet_feed", "GANGLIAN", "nation", "NATION"): "piglet_feed_ganglian",
    ("piglet_feed", "ASSOCIATION", "", "NATION"): "piglet_feed_association",

    # --- 生猪存栏环比 ---
    ("hog_inventory", "YONGYI", "", "NATION"): "hog_inventory_yongyi",
    # GANGLIAN only has small_* variants for hog_inventory
    ("hog_inventory", "GANGLIAN", "small_nation", "NATION"): "hog_inventory_ganglian_small",
    ("hog_inventory", "NYB", "nation", "NATION"): "hog_inventory_nyb_nation",
    ("hog_inventory", "NYB", "scale", "NATION"): "hog_inventory_nyb_scale",
    ("hog_inventory", "NYB", "small", "NATION"): "hog_inventory_nyb_small",

    # --- 育肥猪饲料环比 (DB indicator_code = fattening_feed) ---
    ("fattening_feed", "YONGYI", "", "NATION"): "hog_feed_yongyi",
    ("fattening_feed", "GANGLIAN", "nation", "NATION"): "hog_feed_ganglian",
    ("fattening_feed", "ASSOCIATION", "", "NATION"): "hog_feed_association",
}

# Build the set of indicator_codes and sources we need so the SQL query
# can filter early and avoid scanning unrelated rows.
_NEEDED_INDICATORS = sorted({k[0] for k in INDICATOR_FIELD_MAP})
_NEEDED_SOURCES = sorted({k[1] for k in INDICATOR_FIELD_MAP})

# ---------------------------------------------------------------------------
# Abs-based MoM computations for fields where mom_pct is absent in the DB.
# Format: (indicator_code, source, sub_category, region_code, response_field)
# Only fills the field if not already populated by the mom_pct query above.
# ---------------------------------------------------------------------------
ABS_COMPUTED_FIELDS: list = [
    # 淘汰母猪屠宰环比 — YONGYI/钢联 abs only
    ("cull_slaughter",               "YONGYI",   "",  "NATION", "cull_slaughter_yongyi"),
    ("cull_sow_slaughter",           "GANGLIAN",  "",  "NATION", "cull_slaughter_ganglian"),
    # 能繁母猪存栏环比 — 钢联规模场 uses _large indicator
    ("breeding_sow_inventory_large", "GANGLIAN",  "",  "NATION", "breeding_inventory_ganglian_scale"),
    # 新生仔猪存栏环比 — YONGYI abs only
    ("piglet_inventory",             "YONGYI",    "",  "NATION", "piglet_inventory_yongyi"),
    # 生猪存栏环比 — 钢联全国/规模场 use _total/_large indicator
    ("hog_inventory_total",          "GANGLIAN",  "",  "NATION", "hog_inventory_ganglian_nation"),
    ("hog_inventory_large",          "GANGLIAN",  "",  "NATION", "hog_inventory_ganglian_scale"),
]


def _compute_abs_mom_fields(db: Session, abs_fields: list) -> dict:
    """
    For each abs-field spec, query abs values ordered by month and compute
    month-over-month % change.  Returns {field_name: {month: mom_pct}}.
    """
    result: dict = {}
    for ind, src, sub, rgn, field_name in abs_fields:
        sql = text("""
            SELECT LEFT(month_date, 7) AS month, value
            FROM fact_monthly_indicator
            WHERE indicator_code = :ind
              AND source          = :src
              AND value_type      = 'abs'
              AND COALESCE(sub_category,  '') = :sub
              AND COALESCE(region_code, 'NATION') = :rgn
              AND value IS NOT NULL
            ORDER BY month_date
        """)
        rows = db.execute(sql, {"ind": ind, "src": src, "sub": sub, "rgn": rgn}).fetchall()
        month_vals = {r[0]: float(r[1]) for r in rows}
        sorted_months = sorted(month_vals.keys())

        field_moms: dict = {}
        prev_val = None
        for month in sorted_months:
            curr_val = month_vals[month]
            if prev_val is not None and prev_val != 0:
                field_moms[month] = round((curr_val - prev_val) / prev_val * 100, 2)
            prev_val = curr_val
        result[field_name] = field_moms
    return result


@router.get("/data", response_model=MultiSourceResponse)
async def get_multi_source_data(
    months: int = Query(999, description="显示最近N个月的数据，999表示全部"),
    db: Session = Depends(get_db),
):
    """
    获取多渠道汇总数据
    数据来源：fact_monthly_indicator (hogprice_v3)
    """
    # ------------------------------------------------------------------
    # 1. Query all relevant mom_pct rows in one shot
    # ------------------------------------------------------------------
    indicator_placeholders = ", ".join(
        f":ind_{i}" for i in range(len(_NEEDED_INDICATORS))
    )
    source_placeholders = ", ".join(
        f":src_{i}" for i in range(len(_NEEDED_SOURCES))
    )

    sql = f"""
        SELECT
            LEFT(month_date, 7)                        AS month,
            indicator_code,
            source,
            COALESCE(sub_category, '')                 AS sub_cat,
            COALESCE(region_code, 'NATION')            AS region,
            ROUND(value, 2)                            AS val
        FROM fact_monthly_indicator
        WHERE value_type = 'mom_pct'
          AND indicator_code IN ({indicator_placeholders})
          AND source            IN ({source_placeholders})
        ORDER BY month_date
    """

    params: dict = {}
    for i, ind in enumerate(_NEEDED_INDICATORS):
        params[f"ind_{i}"] = ind
    for i, src in enumerate(_NEEDED_SOURCES):
        params[f"src_{i}"] = src

    rows = db.execute(text(sql), params).fetchall()

    # ------------------------------------------------------------------
    # 2. Pivot rows into {month: {field: value}} using the mapping
    # ------------------------------------------------------------------
    month_data: dict[str, dict[str, float]] = {}

    for row in rows:
        month = row[0]       # YYYY-MM
        ind   = row[1]       # indicator_code
        src   = row[2]       # source
        sub   = row[3]       # sub_category (empty string if NULL)
        rgn   = row[4]       # region_code
        val   = row[5]       # value (already rounded)

        if val is None:
            continue

        val = float(val)

        # Lookup with the exact (ind, src, sub_cat, region) key
        field = INDICATOR_FIELD_MAP.get((ind, src, sub, rgn))
        # Fallback: try with empty sub_category
        if field is None and sub:
            field = INDICATOR_FIELD_MAP.get((ind, src, "", rgn))
        if field is None:
            continue

        if month not in month_data:
            month_data[month] = {}

        # First-writer wins per (month, field) to avoid duplicates
        if field not in month_data[month]:
            month_data[month][field] = val

    # ------------------------------------------------------------------
    # 2.5 Supplement with abs-derived MoM for fields without mom_pct data
    # ------------------------------------------------------------------
    abs_mom = _compute_abs_mom_fields(db, ABS_COMPUTED_FIELDS)
    for field_name, field_moms in abs_mom.items():
        for month, mom_val in field_moms.items():
            if month not in month_data:
                month_data[month] = {}
            # Only fill if not already populated from mom_pct query
            if field_name not in month_data[month]:
                month_data[month][field_name] = mom_val

    # ------------------------------------------------------------------
    # 3. Populate NYB compat fields (*_nyb = copy of *_nyb_nation)
    # ------------------------------------------------------------------
    for month, fields in month_data.items():
        if "breeding_inventory_nyb_nation" in fields and "breeding_inventory_nyb" not in fields:
            fields["breeding_inventory_nyb"] = fields["breeding_inventory_nyb_nation"]
        if "piglet_inventory_nyb_nation" in fields and "piglet_inventory_nyb" not in fields:
            fields["piglet_inventory_nyb"] = fields["piglet_inventory_nyb_nation"]
        if "hog_inventory_nyb_nation" in fields and "hog_inventory_nyb" not in fields:
            fields["hog_inventory_nyb"] = fields["hog_inventory_nyb_nation"]

    # ------------------------------------------------------------------
    # 4. Sort months and apply the limit
    # ------------------------------------------------------------------
    sorted_months = sorted(month_data.keys())
    if months < 999:
        sorted_months = sorted_months[-months:]

    # ------------------------------------------------------------------
    # 5. Build response data points
    # ------------------------------------------------------------------
    data_points: list[MultiSourceDataPoint] = []
    for month in sorted_months:
        fields = month_data.get(month, {})
        data_points.append(MultiSourceDataPoint(month=month, **fields))

    latest_month = sorted_months[-1] if sorted_months else None

    return MultiSourceResponse(
        data=data_points,
        latest_month=latest_month,
    )
