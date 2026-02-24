from app.core.database import Base
from app.models.sys_user import SysUser
from app.models.sys_role import SysRole
from app.models.sys_user_role import SysUserRole
from app.models.import_batch import ImportBatch
from app.models.dim_metric import DimMetric
from app.models.dim_geo import DimGeo
from app.models.dim_company import DimCompany
from app.models.dim_warehouse import DimWarehouse
from app.models.fact_observation import FactObservation
from app.models.chart_template import ChartTemplate
from app.models.report_template import ReportTemplate
from app.models.report_run import ReportRun
# 新数据模型
from app.models.dim_indicator import DimIndicator
from app.models.dim_region import DimRegion
from app.models.dim_contract import DimContract
from app.models.dim_option import DimOption
from app.models.fact_indicator_ts import FactIndicatorTs
from app.models.fact_indicator_metrics import FactIndicatorMetrics
from app.models.fact_futures_daily import FactFuturesDaily
from app.models.fact_options_daily import FactOptionsDaily
from app.models.ingest_error import IngestError
from app.models.ingest_mapping import IngestMapping
# Phase 1: 新增模型
from app.models.dim_source import DimSource
from app.models.dim_location import DimLocation
from app.models.dim_location_alias import DimLocationAlias
from app.models.metric_alias import MetricAlias
from app.models.fact_observation_tag import FactObservationTag
from app.models.raw_file import RawFile
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.ingest_profile import IngestProfile, IngestProfileSheet
from app.models.quick_chart_cache import QuickChartCache

__all__ = [
    "Base",
    "SysUser",
    "SysRole",
    "SysUserRole",
    "ImportBatch",
    "DimMetric",
    "DimGeo",
    "DimCompany",
    "DimWarehouse",
    "FactObservation",
    "ChartTemplate",
    "ReportTemplate",
    "ReportRun",
    # 新数据模型
    "DimIndicator",
    "DimRegion",
    "DimContract",
    "DimOption",
    "FactIndicatorTs",
    "FactIndicatorMetrics",
    "FactFuturesDaily",
    "FactOptionsDaily",
    "IngestError",
    "IngestMapping",
    # Phase 1: 新增模型
    "DimSource",
    "DimLocation",
    "DimLocationAlias",
    "MetricAlias",
    "FactObservationTag",
    "RawFile",
    "RawSheet",
    "RawTable",
    "IngestProfile",
    "IngestProfileSheet",
    "QuickChartCache",
]
