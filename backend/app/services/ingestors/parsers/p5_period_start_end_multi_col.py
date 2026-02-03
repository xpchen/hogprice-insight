"""P5解析器：PERIOD_START_END_MULTI_COL_WITH_GROUP_HEADERS - 周起止 + 规模段/模式列"""
from typing import List, Dict, Any
from datetime import date
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from .base_parser import BaseParser, ObservationDict
from app.utils.dt_parse import parse_period_start_end
from app.utils.value_cleaner import clean_numeric_value_enhanced
from app.utils.dimension_extractor import extract_tags_from_text


class P5PeriodStartEndMultiColParser(BaseParser):
    """P5解析器：处理周起止 + 规模段/模式列的宽表格式"""
    
    def parse(
        self,
        sheet_data: Any,
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析周起止 + 规模段/模式列的宽表格式
        
        示例：周度-养殖利润最新
        """
        observations = []
        
        # 转换为DataFrame
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
        header_row = header_config.get("header_row", 1) - 1
        start_date_col = sheet_config.get("start_date_col", "开始日期")
        end_date_col = sheet_config.get("end_date_col", "结束日期")
        group_headers = sheet_config.get("group_headers", [])  # 分组表头配置
        metric_template = sheet_config.get("metric_template", {})
        sheet_name = sheet_config.get("sheet_name", "")
        
        # 设置表头
        if header_row < len(df):
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:].reset_index(drop=True)
        
        # 查找日期列
        start_col_idx = None
        end_col_idx = None
        for idx, col in enumerate(df.columns):
            col_str = str(col).strip()
            if col_str == start_date_col:
                start_col_idx = idx
            elif col_str == end_date_col:
                end_col_idx = idx
        
        if start_col_idx is None or end_col_idx is None:
            return observations
        
        # 识别分组列（从日期列之后开始）
        group_cols = []
        for idx in range(end_col_idx + 1, len(df.columns)):
            col_name = str(df.columns[idx]).strip()
            if col_name:
                # 从列名提取tags
                col_tags = extract_tags_from_text(col_name)
                group_cols.append((idx, col_name, col_tags))
        
        # 获取指标模板
        metric_key = metric_template.get("metric_key", "")
        metric_name = metric_template.get("metric_name", metric_key)
        unit = metric_template.get("unit")
        template_tags = metric_template.get("tags", {})
        
        # 处理每一行数据
        for row_idx, row in df.iterrows():
            # 解析周期日期
            start_val = row.iloc[start_col_idx] if start_col_idx < len(row) else None
            end_val = row.iloc[end_col_idx] if end_col_idx < len(row) else None
            
            period_start, period_end = parse_period_start_end(start_val, end_val)
            
            if period_end is None:
                continue
            
            # 处理每个分组列
            for col_idx, col_name, col_tags in group_cols:
                if col_idx >= len(row):
                    continue
                
                value_val = row.iloc[col_idx]
                numeric_value, raw_value = clean_numeric_value_enhanced(value_val)
                
                if numeric_value is None and raw_value is None:
                    continue
                
                # 合并tags
                tags = self._merge_tags(template_tags, col_tags)
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_name,
                    metric_key=metric_key,
                    geo_key=None,
                    obs_date=None,
                    period_end=period_end.date() if period_end else None,
                    tags=tags
                )
                
                observation = {
                    "metric_key": metric_key,
                    "metric_name": metric_name,
                    "obs_date": period_end.date() if period_end else None,
                    "period_type": profile_defaults.get("period_type", "week"),
                    "period_start": period_start.date() if period_start else None,
                    "period_end": period_end.date() if period_end else None,
                    "value": numeric_value,
                    "raw_value": raw_value,
                    "geo_code": None,  # 这类表通常没有地理维度
                    "tags": tags,
                    "unit": unit,
                    "dedup_key": dedup_key
                }
                
                observations.append(observation)
        
        return observations
