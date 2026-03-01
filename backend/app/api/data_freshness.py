"""数据新鲜度 API（hogprice_v3）
查询各 fact 表的最新数据日期、行数以及 import_batch 的最近导入时间。
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser

router = APIRouter(prefix=f"{settings.API_V1_STR}/data-freshness", tags=["data-freshness"])

# ---------- 表 → 元数据 ----------
# (表名, 日期列, 来源列, 显示名)
FACT_TABLE_REGISTRY = [
    ("fact_price_daily", "trade_date", "source", "日度价格"),
    ("fact_spread_daily", "trade_date", "source", "日度价差"),
    ("fact_slaughter_daily", "trade_date", "source", "日度屠宰量"),
    ("fact_weekly_indicator", "week_end", "source", "周度指标"),
    ("fact_monthly_indicator", "month_date", "source", "月度指标"),
    ("fact_enterprise_daily", "trade_date", None, "集团企业日度"),
    ("fact_enterprise_monthly", "month_date", None, "集团企业月度"),
    ("fact_carcass_market", "trade_date", None, "白条市场"),
    ("fact_futures_daily", "trade_date", None, "期货日行情"),
    ("fact_futures_basis", "trade_date", None, "基差/月间价差"),
    ("fact_quarterly_stats", "quarter_date", None, "统计局季度"),
]

SOURCE_NAMES = {
    "YONGYI": "涌益咨询",
    "GANGLIAN": "钢联数据",
    "STATS_BUREAU": "统计局",
    "INDUSTRY": "产业数据",
}


class TableFreshnessItem(BaseModel):
    table: str
    label: str
    source: Optional[str] = None
    source_name: Optional[str] = None
    latest_date: Optional[str] = None
    row_count: int = 0
    days_ago: Optional[int] = None


class FreshnessSummary(BaseModel):
    total_tables: int
    total_rows: int
    last_import_time: Optional[str] = None
    oldest_source_date: Optional[str] = None


class DataFreshnessResponse(BaseModel):
    tables: List[TableFreshnessItem]
    summary: FreshnessSummary
    import_batches: List[dict] = []


@router.get("", response_model=DataFreshnessResponse)
async def get_data_freshness(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询各数据表的新鲜度"""
    today = date.today()
    tables: List[TableFreshnessItem] = []
    total_rows = 0

    for table_name, date_col, source_col, label in FACT_TABLE_REGISTRY:
        if source_col:
            # 按 source 分组
            sql = f"""
                SELECT {source_col} AS src,
                       MAX(`{date_col}`) AS latest,
                       COUNT(*) AS cnt
                FROM `{table_name}`
                GROUP BY {source_col}
            """
            rows = db.execute(text(sql)).fetchall()
            for r in rows:
                src = r[0] or "UNKNOWN"
                latest = r[1]
                cnt = r[2]
                total_rows += cnt
                days = (today - latest).days if latest else None
                tables.append(TableFreshnessItem(
                    table=table_name,
                    label=label,
                    source=src,
                    source_name=SOURCE_NAMES.get(src, src),
                    latest_date=latest.isoformat() if latest else None,
                    row_count=cnt,
                    days_ago=days,
                ))
        else:
            sql = f"""
                SELECT MAX(`{date_col}`) AS latest, COUNT(*) AS cnt
                FROM `{table_name}`
            """
            row = db.execute(text(sql)).fetchone()
            latest = row[0] if row else None
            cnt = row[1] if row else 0
            total_rows += cnt
            days = (today - latest).days if latest else None
            tables.append(TableFreshnessItem(
                table=table_name,
                label=label,
                latest_date=latest.isoformat() if latest else None,
                row_count=cnt,
                days_ago=days,
            ))

    # 最近导入批次
    batch_rows = db.execute(text("""
        SELECT id, filename, mode, status, row_count, duration_ms, created_at
        FROM import_batch ORDER BY created_at DESC LIMIT 10
    """)).fetchall()

    import_batches = [
        {
            "id": r[0], "filename": r[1], "mode": r[2], "status": r[3],
            "row_count": r[4], "duration_ms": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
        }
        for r in batch_rows
    ]

    last_import_time = import_batches[0]["created_at"] if import_batches else None

    # 最老的数据源日期
    valid_dates = [t.latest_date for t in tables if t.latest_date]
    oldest = min(valid_dates) if valid_dates else None

    return DataFreshnessResponse(
        tables=tables,
        summary=FreshnessSummary(
            total_tables=len(FACT_TABLE_REGISTRY),
            total_rows=total_rows,
            last_import_time=last_import_time,
            oldest_source_date=oldest,
        ),
        import_batches=import_batches,
    )
