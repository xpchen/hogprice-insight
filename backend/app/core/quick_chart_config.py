"""
快速图表配置：超过此阈值的图表 API 纳入预计算与缓存。
"""
# 响应超过 3 秒则记录日志并纳入快速图表预计算
CHART_RESPONSE_SLOW_THRESHOLD_SEC = 3.0

# 需要计时并可能缓存的图表 API 路径前缀（GET）
CHART_API_PATH_PREFIXES = [
    "/api/v1/price-display/national-price",
    "/api/v1/price-display/fat-std-spread",
    "/api/v1/price-display/price-and-spread",
    "/api/v1/price-display/slaughter",
    "/api/v1/price-display/price-changes",
    "/api/v1/price-display/slaughter-price-trend",
    "/api/v1/price-display/region-spread",
    "/api/v1/price-display/industry-chain",
    "/api/v1/price-display/province-indicators",
    "/api/v1/price-display/frozen-inventory",
    "/api/v1/price-display/live-white-spread",
    "/api/futures/premium",
    "/api/futures/volatility",
    "/api/futures/calendar-spread",
    "/api/v1/multi-source/data",
    "/api/v1/supply-demand/curve",
    "/api/v1/supply-demand/breeding-inventory-price",
    "/api/v1/supply-demand/piglet-price",
    "/api/v1/structure-analysis/data",
    "/api/v1/statistics-bureau",
    "/api/v1/observation",
]

# 导入后预计算的图表 URL（path + 默认 query），仅 GET
# 用于 regenerate：请求该 URL 并将响应写入缓存
QUICK_CHART_PRECOMPUTE_URLS = [
    {"path": "/api/v1/price-display/national-price/seasonality", "params": {}},
    {"path": "/api/v1/price-display/fat-std-spread/seasonality", "params": {}},
    {"path": "/api/v1/price-display/price-and-spread", "params": {}},
    {"path": "/api/v1/price-display/slaughter/lunar", "params": {}},
    {"path": "/api/v1/price-display/price-changes", "params": {"metric_type": "price"}},
    {"path": "/api/v1/price-display/price-changes", "params": {"metric_type": "spread"}},
    {"path": "/api/v1/price-display/slaughter-price-trend/solar", "params": {}},
    {"path": "/api/v1/price-display/slaughter-price-trend/lunar-year", "params": {}},
    {"path": "/api/v1/price-display/region-spread/seasonality", "params": {}},
    {"path": "/api/v1/price-display/industry-chain/seasonality", "params": {}},
    {"path": "/api/futures/premium/v2", "params": {}},
    {"path": "/api/futures/volatility", "params": {}},
    {"path": "/api/futures/calendar-spread", "params": {}},
]


def is_chart_api_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in CHART_API_PATH_PREFIXES)
