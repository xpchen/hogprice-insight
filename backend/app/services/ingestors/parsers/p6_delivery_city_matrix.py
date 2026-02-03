"""P6解析器：DELIVERY_CITY_MATRIX_WITH_META - 交割地市矩阵（省份分组 + 元数据 + 城市×日期）"""
from typing import List, Dict, Any
from datetime import date
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from .base_parser import BaseParser, ObservationDict
from app.utils.dt_parse import parse_date
from app.utils.value_cleaner import clean_numeric_value_enhanced
from app.utils.merged_cell_handler import get_merged_cell_value


class P6DeliveryCityMatrixParser(BaseParser):
    """P6解析器：处理交割地市矩阵格式（最复杂）"""
    
    def parse(
        self,
        sheet_data: Any,
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析交割地市矩阵格式
        
        示例：交割地市出栏价（省份分组 + 元数据 + 城市×日期）
        """
        observations = []
        
        # 需要Worksheet对象来处理复杂结构
        if isinstance(sheet_data, Worksheet):
            worksheet = sheet_data
        else:
            return observations
        
        # 获取配置
        header_config = sheet_config.get("header", {})
        province_group_row = header_config.get("province_group_row", 1)
        meta_start_row = header_config.get("meta_start_row", 2)
        meta_end_row = header_config.get("meta_end_row", 4)
        city_start_row = header_config.get("city_start_row", 5)
        date_start_col = sheet_config.get("date_start_col", 3)
        metric_template = sheet_config.get("metric_template", {})
        sheet_name = sheet_config.get("sheet_name", "")
        
        max_row = worksheet.max_row
        max_col = worksheet.max_column
        
        # 识别省份分组（通过合并单元格或特定标记）
        province_groups = []
        current_province = None
        
        for row_idx in range(city_start_row, max_row + 1):
            # 检查是否是省份分组行
            province_cell = get_merged_cell_value(worksheet, row_idx, 1)
            if province_cell and str(province_cell).strip():
                current_province = str(province_cell).strip()
            
            # 检查是否是城市行
            city_cell = get_merged_cell_value(worksheet, row_idx, 2)
            if city_cell and str(city_cell).strip() and current_province:
                city_name = str(city_cell).strip()
                
                # 读取元数据（升贴水、交易均重等）
                meta_tags = {}
                for meta_row in range(meta_start_row, meta_end_row + 1):
                    meta_label = get_merged_cell_value(worksheet, meta_row, 1)
                    meta_value = get_merged_cell_value(worksheet, meta_row, row_idx)
                    if meta_label and meta_value:
                        meta_key = str(meta_label).strip().lower()
                        meta_tags[meta_key] = str(meta_value).strip()
                
                # 处理日期列
                for col_idx in range(date_start_col, max_col + 1):
                    # 尝试解析列头为日期
                    date_header = get_merged_cell_value(worksheet, province_group_row, col_idx)
                    if not date_header:
                        continue
                    
                    obs_date = None
                    try:
                        parsed_date = parse_date(date_header)
                        if parsed_date:
                            obs_date = parsed_date.date()
                            if obs_date.year < 2000 or obs_date.year > 2100:
                                continue
                    except:
                        continue
                    
                    if obs_date is None:
                        continue
                    
                    # 读取数值
                    cell_value = get_merged_cell_value(worksheet, row_idx, col_idx)
                    numeric_value, raw_value = clean_numeric_value_enhanced(cell_value)
                    
                    if numeric_value is None and raw_value is None:
                        continue
                    
                    # 合并tags
                    template_tags = metric_template.get("tags", {})
                    tags = self._merge_tags(
                        template_tags,
                        {"province": current_province, "city": city_name},
                        meta_tags
                    )
                    
                    # 生成metric_key
                    metric_key = metric_template.get("metric_key", "")
                    if not metric_key:
                        metric_key = f"{sheet_name}_{city_name}".upper().replace(" ", "_")
                    
                    # 生成dedup_key
                    dedup_key = self._generate_dedup_key(
                        source_code=source_code,
                        sheet_name=sheet_name,
                        metric_key=metric_key,
                        geo_key=city_name,
                        obs_date=obs_date,
                        period_end=None,
                        tags=tags
                    )
                    
                    observation = {
                        "metric_key": metric_key,
                        "metric_name": metric_template.get("metric_name", f"{city_name}出栏价"),
                        "obs_date": obs_date,
                        "period_type": profile_defaults.get("period_type", "day"),
                        "period_start": None,
                        "period_end": None,
                        "value": numeric_value,
                        "raw_value": raw_value,
                        "geo_code": city_name,  # 城市代码
                        "tags": tags,
                        "unit": metric_template.get("unit"),
                        "dedup_key": dedup_key
                    }
                    
                    observations.append(observation)
        
        return observations
