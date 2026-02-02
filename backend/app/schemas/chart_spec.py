from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel


class MetricConfig(BaseModel):
    """指标配置"""
    metric_id: int
    name: Optional[str] = None


class FilterConfig(BaseModel):
    """过滤配置"""
    geo_ids: Optional[List[int]] = None
    company_ids: Optional[List[int]] = None
    warehouse_ids: Optional[List[int]] = None
    tags_filter: Optional[Dict[str, Any]] = None


class TimeConfig(BaseModel):
    """时间配置"""
    date_range: Optional[Dict[str, str]] = None  # {"start": "2025-01-01", "end": "2025-12-31"}
    time_dimension: str = "daily"  # daily/weekly/monthly/quarterly/yearly
    years: Optional[List[int]] = None  # 用于seasonality


class TransformConfig(BaseModel):
    """转换配置（可选）"""
    agg: str = "mean"  # mean/last/sum
    x_mode: Optional[str] = None  # week_of_year/month_day (仅seasonality)


class SeasonalityConfig(BaseModel):
    """季节性配置（仅seasonality类型）"""
    x_mode: str = "week_of_year"  # week_of_year | month_day
    agg: str = "mean"  # mean | last


class DisplayConfig(BaseModel):
    """显示配置"""
    title: Optional[str] = None
    unit: Optional[str] = None
    precision: Optional[int] = None  # 小数位数


class ChartSpec(BaseModel):
    """图表配置规范（统一结构）"""
    chart_type: Literal["seasonality", "timeseries"]
    title: str
    metrics: List[MetricConfig]
    filters: FilterConfig
    time: TimeConfig
    transform: Optional[TransformConfig] = None
    seasonality: Optional[SeasonalityConfig] = None  # 仅seasonality类型
    display: Optional[DisplayConfig] = None
