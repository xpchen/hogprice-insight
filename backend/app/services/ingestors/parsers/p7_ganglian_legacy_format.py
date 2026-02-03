"""P7解析器：GANGLIAN_LEGACY_FORMAT - 钢联标准格式"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet
import re

from .base_parser import BaseParser, ObservationDict
from app.utils.dt_parse import parse_date
from app.utils.value_cleaner import clean_numeric_value_enhanced


class P7GanglianLegacyFormatParser(BaseParser):
    """P7解析器：处理钢联标准格式
    
    格式：
    - 第1行：标题（可选）
    - 第2行：指标名称行（包含完整的指标名称，如"商品猪：出栏均价：黑龙江（日）"）
    - 第3行：单位行
    - 第4行：更新时间行
    - 第5行开始：数据行（日期在第一列，数据在后续列）
    """
    
    def parse(
        self,
        sheet_data: Any,
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析钢联标准格式
        """
        observations = []
        
        # 转换为DataFrame（如果还不是）
        if isinstance(sheet_data, Worksheet):
            # 从Worksheet读取数据转换为DataFrame
            data = []
            for row in sheet_data.iter_rows(values_only=True):
                data.append(row)
            df = pd.DataFrame(data)
        else:
            df = sheet_data
        
        if df.empty or len(df) < 5:
            return observations
        
        # 获取配置
        header_config = sheet_config.get("header", {})
        title_row = header_config.get("title_row", 1) - 1  # 转换为0-based
        indicator_row = header_config.get("indicator_row", 2) - 1
        unit_row = header_config.get("unit_row", 3) - 1
        update_time_row = header_config.get("update_time_row", 4) - 1
        data_start_row = header_config.get("data_start_row", 5) - 1
        
        sheet_name = sheet_config.get("sheet_name", "")
        
        # 读取元数据行
        indicator_names = df.iloc[indicator_row] if indicator_row < len(df) else pd.Series()
        unit_values = df.iloc[unit_row] if unit_row < len(df) else pd.Series()
        update_time_values = df.iloc[update_time_row] if update_time_row < len(df) else pd.Series()
        
        # 提取数据部分
        data_df = df.iloc[data_start_row:].copy().reset_index(drop=True)
        if data_df.empty:
            return observations
        
        # 获取最大列数
        max_cols = max(
            len(indicator_names) if len(indicator_names) > 0 else 0,
            len(unit_values) if len(unit_values) > 0 else 0,
            len(update_time_values) if len(update_time_values) > 0 else 0,
            data_df.shape[1] if len(data_df) > 0 else 0
        )
        
        # 第一列是日期列
        date_col_idx = 0
        
        # 处理每一列（从第2列开始，第1列是日期）
        for col_idx in range(1, max_cols):
            if col_idx >= len(indicator_names):
                continue
            
            # 获取指标名称
            raw_header = str(indicator_names.iloc[col_idx]).strip() if col_idx < len(indicator_names) else ""
            if not raw_header or raw_header.lower() in ['nan', 'none', '']:
                continue
            
            # 获取单位
            unit = None
            if col_idx < len(unit_values):
                unit_val = unit_values.iloc[col_idx]
                if pd.notna(unit_val):
                    unit = str(unit_val).strip()
                    if unit.lower() in ['nan', 'none', '']:
                        unit = None
            
            # 获取更新时间
            updated_at_time_str = None
            if col_idx < len(update_time_values):
                update_time_val = update_time_values.iloc[col_idx]
                if pd.notna(update_time_val):
                    try:
                        parsed_time = parse_date(update_time_val)
                        if parsed_time:
                            if isinstance(parsed_time, datetime):
                                updated_at_time_str = parsed_time.isoformat()
                            elif isinstance(parsed_time, date):
                                updated_at_time_str = parsed_time.isoformat()
                            else:
                                updated_at_time_str = str(parsed_time)
                    except:
                        updated_at_time_str = str(update_time_val) if pd.notna(update_time_val) else None
            
            # 处理每一行数据
            for row_idx in range(len(data_df)):
                row = data_df.iloc[row_idx]
                
                # 解析日期（第一列）
                if date_col_idx >= len(row):
                    continue
                    
                date_val = row.iloc[date_col_idx]
                obs_date = None
                if pd.notna(date_val):
                    parsed_date = parse_date(date_val)
                    if parsed_date:
                        obs_date = parsed_date.date()
                        # 检查日期合理性
                        if obs_date.year < 2000 or obs_date.year > 2100:
                            continue
                
                if obs_date is None:
                    continue
                
                # 解析数值
                if col_idx >= len(row):
                    continue
                    
                value_val = row.iloc[col_idx]
                if pd.isna(value_val):
                    continue
                
                numeric_value, raw_value = clean_numeric_value_enhanced(value_val)
                if numeric_value is None:
                    continue
                
                # 从列名中提取省区名称（如果列名格式包含省区信息）
                # 格式示例："生猪标肥：价差：中国（日）" -> 省区="中国"
                # 格式示例："商品猪：出栏均价：黑龙江（日）" -> 省区="黑龙江"
                province_name = None
                geo_code = None
                
                if raw_header and ('：' in raw_header or ':' in raw_header):
                    # 尝试提取省区名称
                    # 方法1：使用正则提取（格式：xxx：xxx：省区（日））
                    match = re.search(r'：([^：（）]+)（', raw_header)
                    if match:
                        province_name = match.group(1).strip()
                    else:
                        # 方法2：分割后取最后一部分
                        parts = raw_header.replace('：', ':').split(':')
                        if len(parts) >= 3:
                            region_part = parts[2].strip()
                            # 移除括号内容
                            if '（' in region_part:
                                province_name = region_part.split('（')[0].strip()
                            else:
                                province_name = region_part.strip()
                
                # 构建ObservationDict
                # 判断是日度还是周度数据（根据sheet名称或配置）
                period_type = "day"  # 默认日度
                period_start = None
                period_end = None
                
                # 检查是否是周度数据
                if "周度" in sheet_name or "周" in sheet_name:
                    period_type = "week"
                    # 对于周度数据，obs_date通常是周期结束日期
                    # 周期开始日期 = 周期结束日期 - 6天
                    period_end = obs_date
                    from datetime import timedelta
                    period_start = obs_date - timedelta(days=6)
                else:
                    # 日度数据
                    period_type = "day"
                    period_end = None
                    period_start = None
                
                # 尝试从sheet_config中获取metric_key模板
                metric_key_template = sheet_config.get("metric_key", "")
                metric_name_template = sheet_config.get("metric_name", "")
                
                # 根据raw_header（列名）来区分不同的指标
                # 对于毛白价差sheet，需要区分毛白价差和价差比率
                if "毛白价差" in sheet_name:
                    if "/" in raw_header or "比率" in raw_header or "比例" in raw_header:
                        # 价差比率列
                        metric_key_template = "GL_D_LIVE_WHITE_SPREAD_RATIO"
                        metric_name_template = "毛白：价差：中国（日） / 商品猪：出栏均价：中国（日）"
                    else:
                        # 毛白价差列
                        metric_key_template = "GL_D_LIVE_WHITE_SPREAD"
                        metric_name_template = "毛白：价差：中国（日）"
                elif not metric_key_template:
                    # 如果没有模板，尝试根据sheet_name生成
                    if "肥标价差" in sheet_name or "标肥价差" in sheet_name:
                        metric_key_template = "GL_D_FAT_STD_SPREAD"
                        metric_name_template = "标肥价差"
                    elif "区域价差" in sheet_name:
                        metric_key_template = "GL_D_REGION_SPREAD"
                        metric_name_template = "区域价差"
                    elif "分省区猪价" in sheet_name:
                        metric_key_template = "GL_D_PRICE_PROVINCE"
                        metric_name_template = "出栏均价"
                    else:
                        # 默认：根据sheet_name生成
                        metric_key_template = f"{source_code}_D_{sheet_name}".upper().replace(" ", "_").replace("（", "_").replace("）", "")
                        metric_name_template = sheet_name
                
                # 如果有省区名称，可以添加到metric_key中（可选）
                metric_key = metric_key_template
                # 使用raw_header作为metric_name，确保每个列都有唯一的metric
                if not metric_name_template or metric_name_template == sheet_name:
                    metric_name_template = raw_header  # 使用原始列名作为metric_name
                
                if province_name and province_name != "中国":
                    # 对于分省区数据，可以在metric_key中包含省区代码
                    # 但为了统一，这里先不添加，让column_mapper处理
                    pass
                
                # 构建tags字典
                tags = {
                    "raw_header": raw_header,
                    "column_name": raw_header,  # 用于column_mapper提取
                }
                
                # 如果提取到了省区名称，添加到tags中
                if province_name:
                    tags["province"] = province_name
                    geo_code = province_name  # 设置geo_code
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_name,
                    metric_key=metric_key,
                    geo_key=geo_code,
                    obs_date=obs_date,
                    period_end=period_end,
                    tags=self._clean_tags(tags)
                )
                
                obs: ObservationDict = {
                    "source_code": source_code,
                    "sheet_name": sheet_name,
                    "metric_key": metric_key,  # 从sheet_config或自动生成
                    "metric_name": metric_name_template,  # 使用raw_header作为metric_name
                    "geo_key": geo_code,  # 从列名提取的省区名称
                    "geo_code": geo_code,  # 从列名提取的省区名称
                    "obs_date": obs_date,
                    "period_type": period_type,
                    "period_start": period_start,
                    "period_end": period_end,
                    "value": numeric_value,
                    "raw_value": raw_value,
                    "unit": unit,
                    "tags": tags,
                    "dedup_key": dedup_key,  # 添加dedup_key
                    "meta": {
                        "unit_row": unit,
                        "update_time_row": updated_at_time_str,
                    },
                    "row_dim": {
                        "date": obs_date,
                    },
                    "column_name": raw_header,  # 用于column_mapper提取
                    "batch_id": batch_id
                }
                
                observations.append(obs)
        
        return observations
