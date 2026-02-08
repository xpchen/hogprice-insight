"""解析器模块"""
from .base_parser import BaseParser, ObservationDict
from .p1_narrow_date_rows import P1NarrowDateRowsParser
from .p2_wide_province_rows import P2WideProvinceRowsParser
from .p3_wide_date_grouped_subcols import P3WideDateGroupedSubcolsParser
from .p4_period_start_end_wide_province import P4PeriodStartEndWideProvinceParser
from .p5_period_start_end_multi_col import P5PeriodStartEndMultiColParser
from .p6_delivery_city_matrix import P6DeliveryCityMatrixParser
from .p7_ganglian_legacy_format import P7GanglianLegacyFormatParser
from .p8_enterprise_daily import P8EnterpriseDailyParser
from .p9_white_strip_market import P9WhiteStripMarketParser

__all__ = [
    "BaseParser",
    "ObservationDict",
    "P1NarrowDateRowsParser",
    "P2WideProvinceRowsParser",
    "P3WideDateGroupedSubcolsParser",
    "P4PeriodStartEndWideProvinceParser",
    "P5PeriodStartEndMultiColParser",
    "P6DeliveryCityMatrixParser",
    "P7GanglianLegacyFormatParser",
    "P8EnterpriseDailyParser",
    "P9WhiteStripMarketParser",
]

# 解析器注册表
PARSER_REGISTRY = {
    "NARROW_DATE_ROWS": P1NarrowDateRowsParser,
    "NARROW_DATE_ROWS_WIDE_PROVINCES": P1NarrowDateRowsParser,  # 变体
    "NARROW_DATE_WIDE_DIM_COLS": P1NarrowDateRowsParser,  # 变体：日期列 + 大区列宽表
    "NARROW_DATE_AUTO": P1NarrowDateRowsParser,  # 变体：日期列时间序列（自动识别）
    "WIDE_PROVINCE_ROWS_DATE_COLS": P2WideProvinceRowsParser,
    "WIDE_DATE_GROUPED_SUBCOLS": P3WideDateGroupedSubcolsParser,
    "PERIOD_START_END_WIDE_PROVINCE": P4PeriodStartEndWideProvinceParser,
    "PERIOD_START_END_WIDE_PROVINCE_WITH_ROW_DIM": P4PeriodStartEndWideProvinceParser,  # 变体
    "PERIOD_START_END_MULTI_METRIC": P4PeriodStartEndWideProvinceParser,  # 变体：周起止 + 多指标列
    "PERIOD_START_END_MULTI_COL_WITH_GROUP_HEADERS": P5PeriodStartEndMultiColParser,
    "PERIOD_END_MULTI_METRIC": P1NarrowDateRowsParser,  # 变体：周结束日期 + 多指标列
    "PERIOD_STRING_ROWS_MULTI_METRIC": P1NarrowDateRowsParser,  # 变体：周期字符串行 + 多指标列
    "MONTHLY_AUTO": P4PeriodStartEndWideProvinceParser,  # 变体：月度表（按表头自动识别）
    "MONTH_ROW_YEAR_COL_MATRIX": P4PeriodStartEndWideProvinceParser,  # 变体：月份行 + 年份列矩阵
    "HISTORY_MATRIX_AUTO": P4PeriodStartEndWideProvinceParser,  # 变体：历史矩阵
    "MULTIHEADER_MATRIX": P3WideDateGroupedSubcolsParser,  # 变体：多表头矩阵
    "MIXED_STATIC_AND_TIME_MATRIX": P1NarrowDateRowsParser,  # 变体：混合静态和时间矩阵
    "CROSS_SECTION_TABLE": P1NarrowDateRowsParser,  # 变体：横截面表
    "NARROW_DATE_MULTI_ROW_DIM": P1NarrowDateRowsParser,  # 变体：日期列 + 多行维度
    "NARROW_DATE_WITH_ROW_DIM_WIDE_PROVINCE": P1NarrowDateRowsParser,  # 变体：日期列 + 行维度 + 省份列
    "NARROW_PERIOD_END_MULTI_METRIC": P1NarrowDateRowsParser,  # 变体：周期结束日期 + 多指标列
    "PERIOD_END_FROM_COL2_START_DERIVED": P4PeriodStartEndWideProvinceParser,  # 变体：从第2列结束日期推导开始日期
    "PERIOD_START_END_PROVINCE_GROUPED_SUBCOLS": P3WideDateGroupedSubcolsParser,  # 变体：周起止 + 省份列 + 子列
    "PERIOD_STRING_ROWS_WIDE_PROVINCE": P4PeriodStartEndWideProvinceParser,  # 变体：周期字符串行 + 省份列
    "DATE_SERIAL_GROUPED_SUBCOLS_WITH_ROW_DIMS": P3WideDateGroupedSubcolsParser,  # 变体：日期序列 + 分组子列 + 行维度
    "NARROW_DATE_ROWS_WIDE_PROVINCES_TRANSPOSED": P2WideProvinceRowsParser,  # 变体：日期行 + 省份列（转置）
    "DELIVERY_CITY_MATRIX_WITH_META": P6DeliveryCityMatrixParser,
    "GANGLIAN_LEGACY_FORMAT": P7GanglianLegacyFormatParser,  # 钢联标准格式：第2行指标名称，第3行单位，第4行更新时间，第5行起数据
    "ENTERPRISE_DAILY": P8EnterpriseDailyParser,  # 企业集团日度数据：CR5日度、西南汇总等
    "WHITE_STRIP_MARKET": P9WhiteStripMarketParser,  # 白条市场跟踪：白条市场、华宝和牧原白条
    "HUABAO_MUYUAN_WHITE_STRIP": P9WhiteStripMarketParser,  # 华宝和牧原白条（使用相同解析器）
}


def get_parser(parser_name: str) -> BaseParser:
    """根据解析器名称获取解析器实例"""
    parser_class = PARSER_REGISTRY.get(parser_name)
    if parser_class is None:
        raise ValueError(f"未知的解析器类型: {parser_name}")
    return parser_class()
