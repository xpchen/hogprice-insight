"""
D3. 销售计划API (hogprice_v3)
查询 fact_enterprise_monthly + fact_enterprise_daily + dim_company
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
    if region != "全部":
        code = next((c for c, n in COMPANY_DISPLAY.items() if n == region), region)
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
        SELECT m.month_date, m.company_code,
               m.company_code AS name,
               m.indicator, m.value
        FROM fact_enterprise_monthly m
        WHERE m.indicator IN (
            {ACTUAL_INDICATORS},
            {PLAN_INDICATORS},
            {RATE_INDICATORS}
        )
        {company_filter}
        ORDER BY m.month_date DESC, m.company_code
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

    # 聚合 (month, code) → {actual, plan, completion_rate}
    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        month_str = r[0].isoformat()[:8] + "01"
        key = f"{month_str}|{r[1]}"
        company_name = COMPANY_DISPLAY.get(r[1], r[1])
        if key not in agg:
            agg[key] = {"month": month_str, "code": r[1], "name": company_name}
        ind = r[3]
        val = float(r[4]) if r[4] is not None else None
        if ind in ACTUAL_SET:
            agg[key]["actual"] = val
        elif ind in PLAN_SET:
            agg[key]["plan"] = val
        elif ind in RATE_SET:
            agg[key]["completion_rate"] = val

    data_points: List[SalesPlanDataPoint] = []
    for item in agg.values():
        plan_val = item.get("plan")
        actual_val = item.get("actual")
        prev_val = item.get("prev_month")
        compl = item.get("completion_rate")

        plan_completion = compl / 100.0 if compl is not None else (
            actual_val / plan_val if actual_val and plan_val else None)
        mom = (actual_val / prev_val - 1) if actual_val and prev_val and prev_val != 0 else None
        pop = (plan_val / prev_val - 1) if plan_val and prev_val and prev_val != 0 else None

        data_points.append(SalesPlanDataPoint(
            date=item["month"], region=item["name"], source="企业集团出栏跟踪",
            actual_output=actual_val, plan_output=plan_val,
            month_on_month=mom, plan_on_plan=pop, plan_completion_rate=plan_completion,
        ))

    if indicator != "全部":
        field_map = {"当月环比": "month_on_month", "计划环比": "plan_on_plan",
                     "计划达成率": "plan_completion_rate", "当月出栏量": "actual_output"}
        field = field_map.get(indicator)
        if field:
            data_points = [p for p in data_points if getattr(p, field) is not None]

    data_points.sort(key=lambda x: x.date, reverse=True)
    latest = data_points[0].date if data_points else None

    return SalesPlanResponse(
        data=data_points, data_source="fact_enterprise_monthly",
        update_time=latest, latest_date=latest)
