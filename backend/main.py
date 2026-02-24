import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, import_excel, metadata, query, export, templates, reports, ingest, ts, futures, options, dashboard, reconciliation, observation, price_display, enterprise_statistics, sales_plan, structure_analysis, group_price, production_indicators, multi_source, supply_demand, statistics_bureau
from app.middleware.chart_timing_and_cache import ChartTimingAndCacheMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

# 全局抑制常见警告
# 抑制 openpyxl 的默认样式警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl.styles.stylesheet')
# 抑制 pandas 的纳秒转换警告
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
# 图表 API：超 3 秒打日志；优先返回预计算缓存
app.add_middleware(ChartTimingAndCacheMiddleware)
# 请求访问日志：记录 method、path、query、status、elapsed_ms
app.add_middleware(RequestLoggingMiddleware)

# 注册路由
app.include_router(auth.router)
app.include_router(import_excel.router)
app.include_router(metadata.router)
app.include_router(query.router)
app.include_router(export.router)
app.include_router(templates.router)
app.include_router(reports.router)
app.include_router(ingest.router)
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


@app.get("/health")
def health():
    return {"status": "ok"}
