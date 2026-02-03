"""P4解析器：PERIOD_START_END_WIDE_PROVINCE - 周起止 + 省份列（周度多数）"""
from typing import List, Dict, Any
from datetime import date
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from .base_parser import BaseParser, ObservationDict
from app.utils.dt_parse import parse_period_start_end
from app.utils.value_cleaner import clean_numeric_value_enhanced


class P4PeriodStartEndWideProvinceParser(BaseParser):
    """P4解析器：处理周起止 + 省份列的宽表格式（周度多数）"""
    
    def parse(
        self,
        sheet_data: Any,
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析周起止 + 省份列的宽表格式
        
        示例：周度-商品猪出栏价、周度-冻品库存
        """
        observations = []
        
        # 转换为DataFrame
        if isinstance(sheet_data, Worksheet):
            # 从Worksheet对象读取数据（不设header，保留原始结构）
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
        # 兼容两种配置格式：
        # 1. {"header": {"header_row": 2}, "start_date_col": "开始日期"}
        # 2. {"header_row": 2, "start_col": "开始日期"}
        header_config = sheet_config.get("header", {})
        header_row = header_config.get("header_row") or sheet_config.get("header_row", 1)
        header_row = header_row - 1  # 转换为0-based索引（例如：header_row=2 -> index=1，即第2行）
        start_date_col = sheet_config.get("start_date_col") or sheet_config.get("start_col", "开始日期")
        end_date_col = sheet_config.get("end_date_col") or sheet_config.get("end_col", "结束日期")
        metric_template = sheet_config.get("metric_template", {})
        sheet_name = sheet_config.get("sheet_name", "")
        
        # 设置表头（使用指定行作为列名）
        # 对于多行表头，只使用配置指定的那一行（通常是最后一行，包含实际列名）
        if header_row < len(df):
            # 使用指定行作为列名
            df.columns = df.iloc[header_row]
            # 跳过表头行，从下一行开始读取数据
            df = df.iloc[header_row + 1:].reset_index(drop=True)
            
            # 调试：打印列名（用于验证多行表头处理是否正确）
            if len(observations) == 0:  # 只在第一次解析时打印
                print(f"      └─ 列名（前10个）: {list(df.columns[:10])}", flush=True)
        
        # 查找日期列（支持"|"分隔的多个列名）
        start_col_idx = None
        end_col_idx = None
        
        # 处理"|"分隔的列名（如"开始日期|起始日期"）
        start_col_names = [name.strip() for name in str(start_date_col).split("|")]
        end_col_names = [name.strip() for name in str(end_date_col).split("|")]
        
        for idx, col in enumerate(df.columns):
            col_str = str(col).strip()
            # 检查开始日期列
            if start_col_idx is None:
                for start_col_name in start_col_names:
                    if col_str == start_col_name:
                        start_col_idx = idx
                        break
            # 检查结束日期列
            if end_col_idx is None:
                for end_col_name in end_col_names:
                    if col_str == end_col_name:
                        end_col_idx = idx
                        break
        
        if start_col_idx is None or end_col_idx is None:
            print(f"      └─ ⚠️  未找到日期列: start_col_idx={start_col_idx}, end_col_idx={end_col_idx}", flush=True)
            print(f"      └─ 查找的列名: start_date_col='{start_date_col}', end_date_col='{end_date_col}'", flush=True)
            print(f"      └─ 实际列名: {list(df.columns)}", flush=True)
            return observations
        
        # 识别省份列（从日期列之后开始）
        # 排除行维度列（如"指标"）和已知的非省份列
        excluded_cols = {"指标", "指标类型", "项目", "日期", "时间", "周期"}
        row_dim_col = sheet_config.get("row_dim_col")
        if row_dim_col:
            excluded_cols.add(str(row_dim_col).strip())
        
        # 全国数据列名（应该被识别为geo_code='NATION'）
        nation_cols = {"全国", "全国1", "全国2", "中国", "NATION"}
        
        province_cols = []
        nation_col_indices = []
        
        for idx in range(end_col_idx + 1, len(df.columns)):
            col_name = str(df.columns[idx]).strip()
            # 跳过排除的列
            if col_name in excluded_cols:
                continue
            
            # 检查是否是全国数据列
            if col_name in nation_cols or (col_name.startswith("全国") and len(col_name) <= 10):
                nation_col_indices.append((idx, col_name))
                continue
            
            # 简单判断：如果列名看起来像省份名
            # 排除包含"以下"、"以上"、"kg"等关键词的列名（这些可能是指标值，不是省份名）
            if col_name and len(col_name) <= 10:
                # 排除包含"以下"、"以上"、"kg"等关键词的列名
                if "以下" not in col_name and "以上" not in col_name and "kg" not in col_name.lower():
                    province_cols.append((idx, col_name))
        
        # 调试：打印识别的省份列
        if len(province_cols) == 0:
            print(f"      └─ ⚠️  未识别到任何省份列！", flush=True)
            print(f"      └─ 日期列之后的列: {list(df.columns[end_col_idx+1:end_col_idx+11])}", flush=True)
        else:
            print(f"      └─ ✓ 识别到 {len(province_cols)} 个省份列: {[name for _, name in province_cols[:10]]}", flush=True)
        
        # 获取指标模板
        metric_key = metric_template.get("metric_key", "") if metric_template else ""
        metric_name = metric_template.get("metric_name", metric_key) if metric_template else sheet_name
        unit = metric_template.get("unit") if metric_template else None
        template_tags = metric_template.get("tags", {}) if metric_template else {}
        
        # 如果metric_key为空，尝试从sheet_config的其他位置获取
        if not metric_key:
            # 尝试从sheet_config顶层获取（某些配置可能直接放在顶层）
            metric_key = sheet_config.get("metric_key", "")
            if metric_key:
                print(f"      ✓ 从sheet_config顶层获取metric_key: {metric_key}", flush=True)
        
        # 调试：如果metric_key仍然为空，打印详细信息
        if not metric_key:
            print(f"      ⚠️  metric_key为空！", flush=True)
            print(f"         sheet_name={sheet_name}", flush=True)
            print(f"         metric_template={metric_template}", flush=True)
            print(f"         sheet_config.keys()={list(sheet_config.keys())[:15]}", flush=True)
            # 尝试从sheet_config直接获取
            if "metric_template" not in sheet_config:
                print(f"         ⚠️  sheet_config中没有metric_template字段！", flush=True)
                # 尝试根据sheet_name推断metric_key（作为最后的回退方案）
                if "体重" in sheet_name or "均重" in sheet_name:
                    if "宰前" in sheet_name or "屠宰" in sheet_name:
                        metric_key = "YY_W_SLAUGHTER_PRELIVE_WEIGHT"
                        print(f"         💡 根据sheet_name推断metric_key: {metric_key}", flush=True)
                    else:
                        metric_key = "YY_W_OUT_WEIGHT"
                        print(f"         💡 根据sheet_name推断metric_key: {metric_key}", flush=True)
        
        # 检查是否有row_dim_col配置（行维度列，如"指标"）
        row_dim_col = sheet_config.get("row_dim_col")
        row_dim_col_idx = None
        if row_dim_col:
            # 查找行维度列索引
            for idx, col in enumerate(df.columns):
                if str(col).strip() == row_dim_col:
                    row_dim_col_idx = idx
                    break
        
        # 处理每一行数据
        debug_count = 0
        for row_idx, row in df.iterrows():
            # 解析周期日期
            start_val = row.iloc[start_col_idx] if start_col_idx < len(row) else None
            end_val = row.iloc[end_col_idx] if end_col_idx < len(row) else None
            
            # 调试：打印前3行的日期值
            if debug_count < 3:
                print(f"      └─ 第{row_idx+1}行: 开始日期={start_val} (type={type(start_val)}), 结束日期={end_val} (type={type(end_val)})", flush=True)
                debug_count += 1
            
            period_start, period_end = parse_period_start_end(start_val, end_val)
            
            if period_end is None:
                if debug_count <= 3:
                    print(f"      └─ ⚠️  第{row_idx+1}行: 日期解析失败，跳过", flush=True)
                continue
            
            # 提取行维度值（如果有）
            row_dim_value = None
            if row_dim_col_idx is not None and row_dim_col_idx < len(row):
                row_dim_value = str(row.iloc[row_dim_col_idx]).strip() if pd.notna(row.iloc[row_dim_col_idx]) else None
            
            # 应用indicator_mapping（如果配置了）
            indicator_mapping = sheet_config.get("indicator_mapping", {})
            mapped_indicator = row_dim_value
            if row_dim_value and indicator_mapping:
                mapped_indicator = indicator_mapping.get(row_dim_value, row_dim_value)
            
            # 根据indicator动态设置单位（如果配置了indicator_unit_mapping）
            indicator_unit_mapping = sheet_config.get("indicator_unit_mapping", {})
            dynamic_unit = unit  # 默认使用模板单位
            if mapped_indicator and indicator_unit_mapping:
                # 优先使用映射后的indicator名称查找单位
                dynamic_unit = indicator_unit_mapping.get(mapped_indicator, dynamic_unit)
                # 如果没找到，尝试使用原始indicator名称
                if dynamic_unit == unit and row_dim_value:
                    dynamic_unit = indicator_unit_mapping.get(row_dim_value, dynamic_unit)
            
            # 处理每个省份列
            for col_idx, province_name in province_cols:
                if col_idx >= len(row):
                    continue
                
                value_val = row.iloc[col_idx]
                numeric_value, raw_value = clean_numeric_value_enhanced(value_val)
                
                if numeric_value is None and raw_value is None:
                    continue
                
                # 合并tags（包含行维度值）
                tags = self._merge_tags(template_tags, {"province": province_name})
                if mapped_indicator:
                    tags["indicator"] = mapped_indicator
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_name,
                    metric_key=metric_key,
                    geo_key=province_name,
                    obs_date=None,
                    period_end=period_end.date() if period_end else None,
                    tags=tags
                )
                
                observation = {
                    "metric_key": metric_key,
                    "metric_name": metric_name,
                    "obs_date": period_end.date() if period_end else None,  # 使用period_end作为obs_date
                    "period_type": profile_defaults.get("period_type", "week"),
                    "period_start": period_start.date() if period_start else None,
                    "period_end": period_end.date() if period_end else None,
                    "value": numeric_value,
                    "raw_value": raw_value,
                    "geo_code": province_name,  # 省份名
                    "tags": tags,
                    "unit": dynamic_unit,  # 使用动态单位
                    "dedup_key": dedup_key
                }
                
                observations.append(observation)
            
            # 处理全国数据列（全国1、全国2等）
            for col_idx, nation_col_name in nation_col_indices:
                if col_idx >= len(row):
                    continue
                
                value_val = row.iloc[col_idx]
                numeric_value, raw_value = clean_numeric_value_enhanced(value_val)
                
                if numeric_value is None and raw_value is None:
                    continue
                
                # 应用indicator_mapping（如果配置了）
                indicator_mapping = sheet_config.get("indicator_mapping", {})
                mapped_indicator = row_dim_value
                if row_dim_value and indicator_mapping:
                    mapped_indicator = indicator_mapping.get(row_dim_value, row_dim_value)
                
                # 根据indicator动态设置单位（如果配置了indicator_unit_mapping）
                indicator_unit_mapping = sheet_config.get("indicator_unit_mapping", {})
                dynamic_unit = unit  # 默认使用模板单位
                if mapped_indicator and indicator_unit_mapping:
                    # 优先使用映射后的indicator名称查找单位
                    dynamic_unit = indicator_unit_mapping.get(mapped_indicator, dynamic_unit)
                    # 如果没找到，尝试使用原始indicator名称
                    if dynamic_unit == unit and row_dim_value:
                        dynamic_unit = indicator_unit_mapping.get(row_dim_value, dynamic_unit)
                
                # 合并tags（包含行维度值和全国列名）
                tags = self._merge_tags(template_tags, {"province": "NATION", "nation_col": nation_col_name})
                if mapped_indicator:
                    tags["indicator"] = mapped_indicator
                
                # 生成dedup_key（使用NATION作为geo_key）
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_name,
                    metric_key=metric_key,
                    geo_key="NATION",  # 全国数据使用NATION
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
                    "geo_code": "NATION",  # 全国数据
                    "tags": tags,
                    "unit": dynamic_unit,  # 使用动态单位
                    "dedup_key": dedup_key
                }
                
                observations.append(observation)
        
        # 调试：打印解析结果统计
        if len(observations) == 0:
            print(f"      └─ ⚠️  解析出0条数据！", flush=True)
            print(f"      └─ 数据行数: {len(df)}", flush=True)
            print(f"      └─ 省份列数: {len(province_cols)}", flush=True)
            print(f"      └─ 全国列数: {len(nation_col_indices)}", flush=True)
        else:
            print(f"      └─ ✓ 解析出 {len(observations)} 条观测值", flush=True)
        
        return observations
