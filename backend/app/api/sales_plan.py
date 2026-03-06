"""
D3. 销售计划API (hogprice_v3)
数据源：
  - fact_enterprise_monthly：集团企业（牧原/温氏等）+ 汇总（广东/四川/贵州/全国CR20/全国CR5）
  - fact_monthly_indicator：涌益（hog_output_volume 实际 + yongyi_planned_output 计划）、钢联（hog_planned_output + hog_slaughter_count）
"""
from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys_user import SysUser

router = APIRouter(prefix="/api/v1/sales-plan", tags=["sales-plan"])

COMPANY_DISPLAY: Dict[str, str] = {
    "MUYUAN": "牧原", "WENS": "温氏", "NEW_HOPE": "新希望",
    "TANGRENSHEN": "唐人神", "ZHENGBANG": "正邦", "DABEINONG": "大北农",
    "TIANBANG": "天邦", "XINWUFENG": "新五丰", "SHENNONG": "神农集团",
}
# 汇总 sheet 写入的 (company_code, region_code) → 前端展示名（与前端区域筛选一致）
REGION_DISPLAY: Dict[tuple, str] = {
    ("TOTAL", "GUANGDONG"): "广东",
    ("TOTAL", "SICHUAN"): "四川",
    ("TOTAL", "GUIZHOU"): "贵州",
    ("CR20", "NATION"): "全国CR20",
    ("CR5", "NATION"): "全国CR5",
}


class SalesPlanDataPoint(BaseModel):
    date: str
    region: str
    source: str
    actual_output: Optional[float] = None
    plan_output: Optional[float] = None
    month_on_month: Optional[float] = None
    plan_on_plan: Optional[float] = None
    plan_completion_rate: Optional[float] = None


class SalesPlanResponse(BaseModel):
    data: List[SalesPlanDataPoint]
    data_source: str
    update_time: Optional[str]
    latest_date: Optional[str]


def _get_ganglian_sales_plan(db: Session) -> List[SalesPlanDataPoint]:
    """钢联：fact_monthly_indicator 月度数据 sheet B列/C列 — 猪：计划出栏量、猪：出栏数（实际）。不限制 value_type 以兼容不同导入。"""
    sql = text("""
        SELECT month_date, indicator_code, value
        FROM fact_monthly_indicator
        WHERE source = 'GANGLIAN'
          AND indicator_code IN ('hog_planned_output', 'hog_slaughter_count')
          AND value IS NOT NULL
        ORDER BY month_date ASC
    """)
    rows = db.execute(sql).fetchall()
    by_month: Dict[str, Dict[str, Optional[float]]] = {}
    for r in rows:
        month_str = r[0].isoformat()[:8] + "01"
        if month_str not in by_month:
            by_month[month_str] = {"plan": None, "actual": None}
        if r[1] == "hog_planned_output":
            by_month[month_str]["plan"] = float(r[2])
        elif r[1] == "hog_slaughter_count":
            by_month[month_str]["actual"] = float(r[2])
    # 环比与文档一致：当月环比=本月实际/上月实际-1，计划环比=当月计划/上月实际出栏-1，计划达成率=当月出栏/当月计划
    sorted_months = sorted(by_month.keys())
    out: List[SalesPlanDataPoint] = []
    for i, month_str in enumerate(sorted_months):
        v = by_month[month_str]
        plan_val = v.get("plan")
        actual_val = v.get("actual")
        prev = by_month.get(sorted_months[i - 1]) if i > 0 else None
        prev_actual = prev.get("actual") if prev else None
        mom = (actual_val / prev_actual - 1) if actual_val and prev_actual and prev_actual != 0 else None
        pop = (plan_val / prev_actual - 1) if plan_val and prev_actual and prev_actual != 0 else None
        compl = (actual_val / plan_val) if (actual_val and plan_val and plan_val != 0) else None
        out.append(SalesPlanDataPoint(
            date=month_str, region="钢联", source="钢联",
            actual_output=actual_val, plan_output=plan_val,
            month_on_month=mom, plan_on_plan=pop, plan_completion_rate=compl,
        ))
    out.reverse()
    return out


def _get_yongyi_sales_plan(db: Session) -> List[SalesPlanDataPoint]:
    """涌益：与旧版一致，实际与计划均来自「月度计划出栏量」同表同单位（万头）。
    实际 = yongyi_actual_sample_sales（上月样本企业合计销售，按行月份-1 写入）；计划 = yongyi_planned_output。
    无 yongyi_actual_sample_sales 时回退为 hog_output_volume(头)/1e4 作为实际(万头)。"""
    sql = text("""
        SELECT month_date, indicator_code, value
        FROM fact_monthly_indicator
        WHERE source = 'YONGYI'
          AND indicator_code IN ('hog_output_volume', 'yongyi_planned_output', 'yongyi_actual_sample_sales')
          AND COALESCE(region_code, 'NATION') = 'NATION'
          AND value IS NOT NULL
        ORDER BY month_date ASC
    """)
    rows = db.execute(sql).fetchall()
    by_month: Dict[str, Dict[str, Optional[float]]] = {}
    for r in rows:
        month_str = r[0].isoformat()[:8] + "01"
        if month_str not in by_month:
            by_month[month_str] = {"plan": None, "actual_wan": None}
        if r[1] == "yongyi_planned_output":
            by_month[month_str]["plan"] = float(r[2])  # 万头
        elif r[1] == "yongyi_actual_sample_sales":
            by_month[month_str]["actual_wan"] = float(r[2])  # 万头，与计划同口径
        elif r[1] == "hog_output_volume":
            # 回退：月度-商品猪出栏量 为头，换算为万头
            v = float(r[2]) / 10000.0
            if by_month[month_str]["actual_wan"] is None:
                by_month[month_str]["actual_wan"] = v
    # 计划环比=当月计划/上月实际出栏-1（与文档一致）
    sorted_months = sorted(by_month.keys())
    out: List[SalesPlanDataPoint] = []
    for i, month_str in enumerate(sorted_months):
        v = by_month[month_str]
        plan_val = v.get("plan")
        actual_wan = v.get("actual_wan")
        prev = by_month.get(sorted_months[i - 1]) if i > 0 else None
        prev_actual = prev.get("actual_wan") if prev else None
        mom = (actual_wan / prev_actual - 1) if actual_wan and prev_actual and prev_actual != 0 else None
        pop = (plan_val / prev_actual - 1) if plan_val and prev_actual and prev_actual != 0 else None
        compl = (actual_wan / plan_val) if (actual_wan and plan_val and plan_val != 0) else None
        out.append(SalesPlanDataPoint(
            date=month_str, region="涌益", source="涌益",
            actual_output=actual_wan, plan_output=plan_val,
            month_on_month=mom, plan_on_plan=pop, plan_completion_rate=compl,
        ))
    out.reverse()
    return out


@router.get("/data", response_model=SalesPlanResponse)
async def get_sales_plan_data(
    indicator: str = Query("全部", description="指标筛选"),
    region: str = Query("全部", description="区域/企业筛选"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取销售计划数据（月度维度）"""
    company_filter = ""
    params: Dict[str, Any] = {}
    # 仅当区域为企业名（牧原、温氏等）时按 company_code 过滤；广东/四川/贵州/全国CR20/全国CR5 在内存中按 region 过滤
    if region != "全部":
        code = next((c for c, n in COMPANY_DISPLAY.items() if n == region), None)
        if code is not None:
            company_filter = " AND m.company_code = :cc"
            params["cc"] = code

    # fact_enterprise_monthly uses 'indicator' column (not metric_type)
    # and supports both Chinese and English indicator names
    ACTUAL_INDICATORS = (
        "'actual_output_monthly','实际出栏量','实际出栏量_月度'"
    )
    PLAN_INDICATORS = (
        "'planned_output_monthly','计划出栏量','计划出栏量_月度'"
    )
    RATE_INDICATORS = (
        "'plan_completion_rate_monthly','完成率_月度','完成度_月度','完成率','完成度'"
    )

    sql = f"""
        SELECT m.month_date, m.company_code, m.region_code,
               m.indicator, m.value
        FROM fact_enterprise_monthly m
        WHERE m.indicator IN (
            {ACTUAL_INDICATORS},
            {PLAN_INDICATORS},
            {RATE_INDICATORS}
        )
        {company_filter}
        ORDER BY m.month_date DESC, m.company_code, m.region_code
    """
    rows = db.execute(text(sql), params).fetchall()

    # indicator → logical category mapping
    ACTUAL_SET = {
        'actual_output_monthly', '实际出栏量', '实际出栏量_月度',
    }
    PLAN_SET = {
        'planned_output_monthly', '计划出栏量', '计划出栏量_月度',
    }
    RATE_SET = {
        'plan_completion_rate_monthly', '完成率_月度', '完成度_月度', '完成率', '完成度',
    }

    def _region_name(company_code: str, region_code: str) -> str:
        rn = REGION_DISPLAY.get((company_code, region_code or "NATION"))
        if rn is not None:
            return rn
        return COMPANY_DISPLAY.get(company_code, company_code)

    # 聚合 (month, company_code, region_code) → {actual, plan, completion_rate}，避免广东/四川/贵州被合并
    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        month_str = r[0].isoformat()[:8] + "01"
        company_code = r[1]
        region_code = (r[2] or "NATION") if len(r) > 2 else "NATION"
        key = f"{month_str}|{company_code}|{region_code}"
        name = _region_name(company_code, region_code)
        if key not in agg:
            agg[key] = {"month": month_str, "code": company_code, "region_code": region_code, "name": name}
        ind = r[3]
        val = float(r[4]) if r[4] is not None else None
        if ind in ACTUAL_SET:
            agg[key]["actual"] = val
        elif ind in PLAN_SET:
            agg[key]["plan"] = val
        elif ind in RATE_SET:
            agg[key]["completion_rate"] = val

    # 按 (company_code, region_code) 分组、按月份升序，填上月 actual/plan 用于计算环比（与结构分析/旧逻辑一致：环比由绝对值计算）
    group_key = lambda item: (item["code"], item["region_code"])
    grouped: Dict[tuple, List[Dict]] = {}
    for item in agg.values():
        k = group_key(item)
        if k not in grouped:
            grouped[k] = []
        grouped[k].append(item)
    for group in grouped.values():
        group.sort(key=lambda x: x["month"])
        for i, item in enumerate(group):
            prev_item = group[i - 1] if i > 0 else None
            item["prev_actual"] = prev_item.get("actual") if prev_item else None
            item["prev_plan"] = prev_item.get("plan") if prev_item else None

    data_points: List[SalesPlanDataPoint] = []
    for item in agg.values():
        plan_val = item.get("plan")
        actual_val = item.get("actual")
        prev_actual = item.get("prev_actual")
        prev_plan = item.get("prev_plan")
        compl = item.get("completion_rate")

        plan_completion = compl / 100.0 if compl is not None else (
            actual_val / plan_val if actual_val and plan_val else None)
        mom = (actual_val / prev_actual - 1) if actual_val and prev_actual and prev_actual != 0 else None
        pop = (plan_val / prev_actual - 1) if plan_val and prev_actual and prev_actual != 0 else None  # 计划环比=当月计划/上月实际

        data_points.append(SalesPlanDataPoint(
            date=item["month"], region=item["name"], source="企业集团出栏跟踪",
            actual_output=actual_val, plan_output=plan_val,
            month_on_month=mom, plan_on_plan=pop, plan_completion_rate=plan_completion,
        ))

    # 合并涌益、钢联（fact_monthly_indicator）
    data_points.extend(_get_yongyi_sales_plan(db))
    data_points.extend(_get_ganglian_sales_plan(db))

    # 区域筛选：广东/四川/贵州/全国CR20/全国CR5/涌益/钢联 在内存中按 region 过滤
    if region != "全部":
        data_points = [p for p in data_points if p.region == region]

    if indicator != "全部":
        # 与前端列头一致：中文指标名 → 字段
        field_map = {
            "当月环比": "month_on_month", "计划环比": "plan_on_plan",
            "计划完成率": "plan_completion_rate", "计划达成率": "plan_completion_rate",
            "实际出栏量": "actual_output", "计划出栏量": "plan_output",
        }
        field = field_map.get(indicator)
        if field:
            data_points = [p for p in data_points if getattr(p, field) is not None]

    data_points.sort(key=lambda x: x.date, reverse=True)
    latest = data_points[0].date if data_points else None

    return SalesPlanResponse(
        data=data_points,
        data_source="fact_enterprise_monthly,fact_monthly_indicator（企业集团、涌益、钢联）",
        update_time=latest, latest_date=latest)
