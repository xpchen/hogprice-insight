"""P2解析器：WIDE_PROVINCE_ROWS_DATE_COLS - 省份行 + 日期列（需要unpivot）"""
from typing import List, Dict, Any
from datetime import date
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from .base_parser import BaseParser, ObservationDict
from app.utils.dt_parse import parse_date
from app.utils.value_cleaner import clean_numeric_value_enhanced


class P2WideProvinceRowsParser(BaseParser):
    """P2解析器：处理省份行 + 日期列的宽表格式（需要unpivot）"""
    
    def parse(
        self,
        sheet_data: Any,
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析宽表格式（省份行 + 日期列）
        
        示例：屠宰企业日度屠宰量
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
        province_col_name = sheet_config.get("province_col", "省份")
        metric_template = sheet_config.get("metric_template", {})
        sheet_name = sheet_config.get("sheet_name", "")
        
        # 设置表头
        if header_row < len(df):
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:].reset_index(drop=True)
        
        # 查找省份列
        province_col_idx = None
        for idx, col in enumerate(df.columns):
            if str(col).strip() == province_col_name:
                province_col_idx = idx
                break
        
        if province_col_idx is None:
            return observations
        
        # 获取指标模板
        metric_key = metric_template.get("metric_key", "")
        metric_name = metric_template.get("metric_name", metric_key)
        unit = metric_template.get("unit")
        template_tags = metric_template.get("tags", {})
        
        # 识别日期列（从第二列开始，跳过省份列）
        date_cols = []
        for idx in range(province_col_idx + 1, len(df.columns)):
            col_name = str(df.columns[idx]).strip()
            # 尝试解析为日期
            test_val = df.iloc[0, idx] if len(df) > 0 else None
            if test_val is not None:
                parsed_date = parse_date(test_val)
                if parsed_date:
                    date_cols.append((idx, parsed_date.date()))
        
        # 处理每一行（省份）
        for row_idx, row in df.iterrows():
            province_name = row.iloc[province_col_idx]
            if pd.isna(province_name) or not str(province_name).strip():
                continue
            
            province_code = str(province_name).strip()
            
            # 处理每个日期列
            for col_idx, obs_date in date_cols:
                if col_idx >= len(row):
                    continue
                
                value_val = row.iloc[col_idx]
                numeric_value, raw_value = clean_numeric_value_enhanced(value_val)
                
                if numeric_value is None and raw_value is None:
                    continue
                
                # 合并tags
                tags = self._merge_tags(template_tags, {"province": province_code})
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_name,
                    metric_key=metric_key,
                    geo_key=province_code,
                    obs_date=obs_date,
                    period_end=None,
                    tags=tags
                )
                
                observation = {
                    "metric_key": metric_key,
                    "metric_name": metric_name,
                    "obs_date": obs_date,
                    "period_type": profile_defaults.get("period_type", "day"),
                    "period_start": None,
                    "period_end": None,
                    "value": numeric_value,
                    "raw_value": raw_value,
                    "geo_code": province_code,
                    "tags": tags,
                    "unit": unit,
                    "dedup_key": dedup_key
                }
                
                observations.append(observation)
        
        return observations
