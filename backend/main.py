import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import (
    auth, metadata, ts, futures, options, dashboard, reconciliation,
    observation, price_display, enterprise_statistics, sales_plan,
    structure_analysis, group_price, production_indicators, multi_source,
    supply_demand, statistics_bureau, ingest, query, export, data_freshness,
)
from app.middleware.chart_timing_and_cache import ChartTimingAndCacheMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

# 全局抑制常见警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl.styles.stylesheet')
warnings.filterwarnings('ignore', message='Discarding nonzero nanoseconds in conversion')

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ChartTimingAndCacheMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# 注册路由 —— 核心业务 API（已改写为 hogprice_v3）
app.include_router(auth.router)
app.include_router(metadata.router)
app.include_router(ts.router)
app.include_router(futures.router)
app.include_router(options.router)
app.include_router(dashboard.router)
app.include_router(reconciliation.router)
app.include_router(observation.router)
app.include_router(price_display.router)
app.include_router(enterprise_statistics.router)
app.include_router(sales_plan.router)
app.include_router(structure_analysis.router)
app.include_router(group_price.router)
app.include_router(production_indicators.router)
app.include_router(multi_source.router)
app.include_router(supply_demand.router)
app.include_router(statistics_bureau.router)
# 数据导入（已简化为 import_tool）
app.include_router(ingest.router)
# 通用查询 & 导出（精简版）
app.include_router(query.router)
app.include_router(export.router)
# 数据新鲜度
app.include_router(data_freshness.router)


@app.get("/health")
def health():
    return {"status": "ok"}
