"""P1解析器：NARROW_DATE_ROWS - 日期行 + 指标列（窄表）"""
from typing import List, Dict, Any, Optional
from datetime import date
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from .base_parser import BaseParser, ObservationDict
from app.utils.dt_parse import parse_date
from app.utils.value_cleaner import clean_numeric_value_enhanced
from app.utils.dimension_extractor import extract_tags_from_column_name


class P1NarrowDateRowsParser(BaseParser):
    """P1解析器：处理日期列 + 指标列的窄表格式"""
    
    def parse(
        self,
        sheet_data: Any,
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析窄表格式（日期列 + 指标列）
        
        示例：价格+宰量、市场主流标猪肥猪均价方便作图
        """
        observations = []
        
        # 转换为DataFrame（如果还不是）
        if isinstance(sheet_data, Worksheet):
            # 从Worksheet对象读取数据
            data = list(sheet_data.values)
            df = pd.DataFrame(data)
        elif isinstance(sheet_data, pd.DataFrame):
            df = sheet_data
        else:
            # 尝试作为文件路径读取
            df = pd.read_excel(sheet_data, engine='openpyxl', header=None)
        
        if df.empty:
            return observations
        
        # 获取配置
        header_config = sheet_config.get("header", {})
        header_row = header_config.get("header_row") or sheet_config.get("header_row", 1)
        header_row = header_row - 1  # 转换为0-based
        date_col_name = sheet_config.get("date_col", "日期")
        
        # 支持两种配置格式：metrics 或 metrics_from_columns
        metrics_config = sheet_config.get("metrics_from_columns") or sheet_config.get("metrics", [])
        geo_config = sheet_config.get("geo", {})
        sheet_name = sheet_config.get("sheet_name", "")
        
        # 设置表头
        if header_row < len(df):
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:].reset_index(drop=True)
        
        # 查找日期列
        date_col_idx = None
        for idx, col in enumerate(df.columns):
            if str(col).strip() == date_col_name:
                date_col_idx = idx
                break
        
        if date_col_idx is None:
            return observations  # 找不到日期列
        
        # 处理每个指标
        for metric_config in metrics_config:
            metric_key = metric_config.get("metric_key")
            metric_name = metric_config.get("metric_name", metric_key)
            unit = metric_config.get("unit")
            
            # 支持两种列名格式：col（metrics_from_columns）或 raw_header（metrics）
            col_name = metric_config.get("col") or metric_config.get("raw_header", "")
            metric_tags = metric_config.get("tags", {})
            use_col_occurrence = metric_config.get("use_col_occurrence", 1)  # 默认使用第1次出现
            
            # 查找指标列（支持 use_col_occurrence）
            metric_col_idx = None
            occurrence_count = 0
            for idx, col in enumerate(df.columns):
                if str(col).strip() == col_name:
                    occurrence_count += 1
                    if occurrence_count == use_col_occurrence:
                        metric_col_idx = idx
                        break
            
            if metric_col_idx is None:
                continue  # 找不到指标列
            
            # 处理每一行数据
            for row_idx, row in df.iterrows():
                # 解析日期
                date_val = row.iloc[date_col_idx]
                parsed_date = None
                if date_val is not None:
                    parsed_date = parse_date(date_val)
                    if parsed_date:
                        parsed_date = parsed_date.date()
                        # 检查日期合理性
                        if parsed_date.year < 2000 or parsed_date.year > 2100:
                            continue
                
                if parsed_date is None:
                    continue
                
                # 对于 PERIOD_END_MULTI_METRIC，使用 period_end 而不是 obs_date
                # 检查是否是周期结束日期格式
                is_period_end = sheet_config.get("parser") == "PERIOD_END_MULTI_METRIC" or \
                               sheet_config.get("parser") == "NARROW_PERIOD_END_MULTI_METRIC"
                
                obs_date = parsed_date
                period_end = parsed_date if is_period_end else None
                period_start = None
                
                # 解析数值
                value_val = row.iloc[metric_col_idx]
                numeric_value, raw_value = clean_numeric_value_enhanced(value_val)
                
                if numeric_value is None and raw_value is None:
                    continue
                
                # 处理地理位置
                geo_code = None
                geo_type = geo_config if isinstance(geo_config, str) else geo_config.get("type", "NATION")
                if geo_type == "NATION":
                    geo_code = "NATION"
                elif geo_type == "PROVINCE_FROM_COLUMN":
                    # 从列名提取省份（对于"各省份均价"这种）
                    province_cols = sheet_config.get("province_cols", "*")
                    if province_cols == "*" and col_name:
                        # 尝试从列名提取省份
                        pass  # TODO: 实现省份提取
                
                # 合并tags
                tags = self._merge_tags(metric_tags)
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_name,
                    metric_key=metric_key,
                    geo_key=geo_code,
                    obs_date=obs_date,
                    period_end=period_end,
                    tags=tags
                )
                
                observation = {
                    "metric_key": metric_key,
                    "metric_name": metric_name,
                    "obs_date": obs_date,
                    "period_type": profile_defaults.get("period_type", "week" if is_period_end else "day"),
                    "period_start": period_start,
                    "period_end": period_end,
                    "value": numeric_value,
                    "raw_value": raw_value,
                    "geo_code": geo_code,
                    "tags": tags,
                    "unit": unit,
                    "dedup_key": dedup_key
                }
                
                observations.append(observation)
        
        return observations
