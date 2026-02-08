"""P8解析器：企业集团日度出栏数据（CR5日度、西南汇总等）"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import re

from .base_parser import BaseParser, ObservationDict
from app.utils.dt_parse import parse_date
from app.utils.value_cleaner import clean_numeric_value_enhanced


class P8EnterpriseDailyParser(BaseParser):
    """P8解析器：处理企业集团日度出栏数据"""
    
    def parse(
        self,
        sheet_data: Any,
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析企业集团日度数据
        
        支持格式：
        1. CR5日度：第1行表头，第2行开始数据，第一列是Excel日期序列号
        2. 西南汇总：第1行地区分组，第2行指标名称，第3行开始数据
        """
        observations = []
        
        # 转换为DataFrame
        if isinstance(sheet_data, pd.DataFrame):
            df = sheet_data
        else:
            # 从Worksheet对象读取数据
            data = list(sheet_data.values)
            df = pd.DataFrame(data)
        
        if df.empty:
            return observations
        
        sheet_name = sheet_config.get("sheet_name", "")
        
        # 根据sheet名称选择解析方式
        if "CR5" in sheet_name or "cr5" in sheet_name.lower():
            return self._parse_cr5_daily(df, sheet_config, source_code, batch_id)
        elif "西南汇总" in sheet_name or "southwest" in sheet_name.lower():
            return self._parse_southwest_summary(df, sheet_config, source_code, batch_id)
        elif sheet_name == "汇总":
            # 汇总sheet（旬度数据，包含广东、四川、贵州、全国CR20、全国CR5）
            return self._parse_summary_sheet(df, sheet_config, source_code, batch_id)
        elif "重点省区汇总" in sheet_name:
            return self._parse_province_summary(df, sheet_config, source_code, batch_id)
        else:
            # 默认尝试CR5格式
            return self._parse_cr5_daily(df, sheet_config, source_code, batch_id)
    
    def _parse_cr5_daily(
        self,
        df: pd.DataFrame,
        sheet_config: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """解析CR5日度数据"""
        observations = []
        
        if df.shape[0] < 2:
            return observations
        
        # 第1行是表头
        header_row = df.iloc[0].tolist()
        
        # 从第2行开始是数据（第1列是Excel日期序列号）
        data_start_row = 1
        
        # 解析表头，找到指标列
        metric_columns = {}
        for idx, header in enumerate(header_row):
            if pd.isna(header) or str(header).strip() == "":
                continue
            
            header_str = str(header).strip()
            
            # 识别指标类型
            if "实际出栏" in header_str or "实际成交" in header_str:
                metric_columns[idx] = {
                    "metric_name": "日度出栏",
                    "metric_key": "CR5_DAILY_OUTPUT",
                    "unit": "头"
                }
            elif "月度计划" in header_str or "计划日均" in header_str or "计划量" in header_str:
                metric_columns[idx] = {
                    "metric_name": "计划量",
                    "metric_key": "CR5_MONTHLY_PLAN",
                    "unit": "头"
                }
            elif "全国均价" in header_str or "价格" in header_str:
                metric_columns[idx] = {
                    "metric_name": "价格",
                    "metric_key": "CR5_PRICE",
                    "unit": "元/公斤"
                }
            elif header_str in ["牧原", "温氏", "双胞胎", "新希望", "德康"]:
                metric_columns[idx] = {
                    "metric_name": "日度出栏",
                    "metric_key": f"CR5_COMPANY_{header_str}",
                    "unit": "头",
                    "company": header_str
                }
            elif "均重" in header_str:
                metric_columns[idx] = {
                    "metric_name": "均重",
                    "metric_key": "CR5_AVG_WEIGHT",
                    "unit": "公斤"
                }
        
        # 解析数据行
        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            
            # 第1列是Excel日期序列号
            date_serial = row.iloc[0]
            if pd.isna(date_serial):
                continue
            
            # 转换Excel日期序列号为实际日期
            try:
                if isinstance(date_serial, (int, float)):
                    # Excel日期序列号（从1900-01-01开始）
                    excel_epoch = datetime(1899, 12, 30)
                    obs_date = excel_epoch + pd.Timedelta(days=int(date_serial))
                    obs_date = obs_date.date()
                else:
                    # 尝试直接解析日期字符串
                    obs_date = parse_date(date_serial)
                    if obs_date:
                        obs_date = obs_date.date()
                    else:
                        continue
            except:
                continue
            
            # 解析每个指标列的值
            for col_idx, metric_info in metric_columns.items():
                if col_idx >= len(row):
                    continue
                
                value = row.iloc[col_idx]
                if pd.isna(value) or value == "":
                    continue
                
                # 清理数值（返回tuple: (numeric_value, raw_value)）
                cleaned_result = clean_numeric_value_enhanced(value)
                if cleaned_result is None or cleaned_result[0] is None:
                    continue
                cleaned_value, raw_value = cleaned_result
                
                # 构建tags
                tags = {}
                if "company" in metric_info:
                    tags["company"] = metric_info["company"]
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_config.get("sheet_name", ""),
                    metric_key=metric_info["metric_key"],
                    geo_key=None,
                    obs_date=obs_date,
                    period_end=None,
                    tags=tags
                )
                
                # 构建observation字典
                obs = {
                    "obs_date": obs_date,
                    "metric_name": metric_info["metric_name"],
                    "metric_key": metric_info["metric_key"],
                    "value": cleaned_value,
                    "unit": metric_info.get("unit"),
                    "tags": tags,
                    "geo_code": None,
                    "period_type": "day",
                    "raw_value": raw_value if raw_value else (str(value) if value else None),
                    "dedup_key": dedup_key
                }
                observations.append(obs)
        
        return observations
    
    def _parse_southwest_summary(
        self,
        df: pd.DataFrame,
        sheet_config: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """解析西南汇总数据"""
        observations = []
        
        if df.shape[0] < 3:
            return observations
        
        # 第1行：地区分组（四川、广西、贵州、西南样本企业）
        # 第2行：指标名称（挂牌、实际成交、成交率、计划日均、最新日均、价格MS、出栏、量）
        # 第3行开始：数据（第1列是日期）
        
        region_row = df.iloc[0].tolist()
        metric_row = df.iloc[1].tolist()
        
        # 解析地区分组
        regions = {}
        current_region = None
        for idx, cell in enumerate(region_row):
            if pd.notna(cell) and str(cell).strip():
                region_name = str(cell).strip()
                if region_name in ["四川", "广西", "贵州", "西南样本企业"]:
                    current_region = region_name
                    regions[idx] = current_region
        
        # 解析指标列
        metric_columns = {}
        for idx, metric_name in enumerate(metric_row):
            if pd.isna(metric_name) or str(metric_name).strip() == "":
                continue
            
            metric_str = str(metric_name).strip()
            
            # 确定指标类型和单位
            if "实际成交" in metric_str:
                metric_columns[idx] = {
                    "metric_name": "日度出栏",
                    "metric_key": "SOUTHWEST_ACTUAL_OUTPUT",
                    "unit": "头"
                }
            elif "计划日均" in metric_str:
                metric_columns[idx] = {
                    "metric_name": "计划出栏",
                    "metric_key": "SOUTHWEST_PLAN_OUTPUT",
                    "unit": "头"
                }
            elif "成交率" in metric_str or "完成率" in metric_str:
                metric_columns[idx] = {
                    "metric_name": "完成率",
                    "metric_key": "SOUTHWEST_COMPLETION_RATE",
                    "unit": "%"
                }
            elif "价格" in metric_str or "MS" in metric_str:
                metric_columns[idx] = {
                    "metric_name": "价格",
                    "metric_key": "SOUTHWEST_PRICE",
                    "unit": "元/公斤"
                }
            elif metric_str == "量" or "出栏" in metric_str:
                metric_columns[idx] = {
                    "metric_name": "出栏量",
                    "metric_key": "SOUTHWEST_OUTPUT",
                    "unit": "头"
                }
            elif metric_str == "重":
                metric_columns[idx] = {
                    "metric_name": "均重",
                    "metric_key": "SOUTHWEST_AVG_WEIGHT",
                    "unit": "公斤"
                }
            elif metric_str == "价":
                metric_columns[idx] = {
                    "metric_name": "价格",
                    "metric_key": "SOUTHWEST_PRICE",
                    "unit": "元/公斤"
                }
        
        # 解析数据行（从第3行开始）
        for row_idx in range(2, len(df)):
            row = df.iloc[row_idx]
            
            # 第1列是日期（第2列也可能是日期）
            date_val = None
            for col_idx in [0, 1]:
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if pd.notna(val):
                        parsed_date = parse_date(val)
                        if parsed_date:
                            date_val = parsed_date.date()
                            break
            
            if not date_val:
                continue
            
            # 解析每个指标列
            for col_idx, metric_info in metric_columns.items():
                if col_idx >= len(row):
                    continue
                
                value = row.iloc[col_idx]
                if pd.isna(value) or value == "" or value == "#N/A":
                    continue
                
                # 清理数值（返回tuple: (numeric_value, raw_value)）
                cleaned_result = clean_numeric_value_enhanced(value)
                if cleaned_result is None or cleaned_result[0] is None:
                    continue
                cleaned_value, raw_value = cleaned_result
                
                # 确定地区
                region_name = None
                # 查找该列对应的地区（向前查找最近的地区）
                for reg_col_idx in range(col_idx, -1, -1):
                    if reg_col_idx in regions:
                        region_name = regions[reg_col_idx]
                        break
                
                # 构建tags
                tags = {}
                if region_name:
                    tags["region"] = region_name
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_config.get("sheet_name", ""),
                    metric_key=metric_info["metric_key"],
                    geo_key=region_name if region_name else None,
                    obs_date=date_val,
                    period_end=None,
                    tags=tags
                )
                
                # 构建observation字典
                obs = {
                    "obs_date": date_val,
                    "metric_name": metric_info["metric_name"],
                    "metric_key": metric_info["metric_key"],
                    "value": cleaned_value,
                    "unit": metric_info.get("unit"),
                    "tags": tags,
                    "geo_code": region_name if region_name else None,
                    "period_type": "day",
                    "raw_value": raw_value if raw_value else (str(value) if value else None),
                    "dedup_key": dedup_key
                }
                observations.append(obs)
        
        return observations
    
    def _parse_province_summary(
        self,
        df: pd.DataFrame,
        sheet_config: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """解析重点省区汇总数据"""
        observations = []
        
        if df.shape[0] < 3:
            return observations
        
        # 第1行：地区分组（西南、华南、东北等）
        # 第2行：省份名称（四川、贵州、广西、合计、江西、广东、湖南、黑龙江、吉林、内蒙古、辽宁、合计、陕西）
        # 第3行开始：数据（第1列是日期，第2列开始是各省份的计划量）
        
        province_row = df.iloc[1].tolist()
        
        # 解析省份列索引
        province_columns = {}
        for idx, province_name in enumerate(province_row):
            if pd.notna(province_name) and str(province_name).strip():
                province_str = str(province_name).strip()
                # 跳过"合计"列和空列
                if province_str != "合计" and province_str:
                    province_columns[idx] = province_str
        
        # 解析数据行（从第3行开始）
        for row_idx in range(2, len(df)):
            row = df.iloc[row_idx]
            
            # 第1列或第2列可能是日期
            date_val = None
            for col_idx in [0, 1]:
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if pd.notna(val):
                        parsed_date = parse_date(val)
                        if parsed_date:
                            date_val = parsed_date.date()
                            break
            
            if not date_val:
                continue
            
            # 解析每个省份列
            for col_idx, province_name in province_columns.items():
                if col_idx >= len(row):
                    continue
                
                value = row.iloc[col_idx]
                if pd.isna(value) or value == "" or value == "#N/A":
                    continue
                
                # 清理数值
                cleaned_result = clean_numeric_value_enhanced(value)
                if cleaned_result is None or cleaned_result[0] is None:
                    continue
                cleaned_value, raw_value = cleaned_result
                
                # 构建tags
                tags = {"region": province_name}
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_config.get("sheet_name", ""),
                    metric_key="PROVINCE_PLAN",
                    geo_key=province_name,
                    obs_date=date_val,
                    period_end=None,
                    tags=tags
                )
                
                # 构建observation字典
                obs = {
                    "obs_date": date_val,
                    "metric_name": "计划量",
                    "metric_key": "PROVINCE_PLAN",
                    "value": cleaned_value,
                    "unit": "头",
                    "tags": tags,
                    "geo_code": province_name,
                    "period_type": "day",
                    "raw_value": raw_value if raw_value else (str(value) if value else None),
                    "dedup_key": dedup_key
                }
                observations.append(obs)
        
        return observations
    
    def _parse_summary_sheet(
        self,
        df: pd.DataFrame,
        sheet_config: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """解析汇总sheet（旬度数据：广东、四川、贵州、全国CR20、全国CR5）"""
        observations = []
        
        if df.shape[0] < 3:
            return observations
        
        # 第1行：地区分组（广东、四川、贵州、全国CR20、全国CR5）
        # 第2行：指标名称（出栏计划、实际出栏量、计划完成率、均重等）
        # 第3行开始：数据（第1列=时间类型，第2列=日期，第3列开始=数据）
        
        row1 = df.iloc[0].tolist()
        row2 = df.iloc[1].tolist()
        
        # 解析地区分组和指标映射
        # 地区分组：{地区名: (开始列索引, 结束列索引)}
        regions_map = {}
        current_region = None
        region_start_col = None
        
        for idx, val in enumerate(row1):
            if pd.notna(val) and str(val).strip():
                val_str = str(val).strip()
                if val_str in ["广东", "四川", "贵州", "全国CR20", "全国CR5"]:
                    if current_region:
                        regions_map[current_region] = (region_start_col, idx)
                    current_region = val_str
                    region_start_col = idx
        if current_region:
            regions_map[current_region] = (region_start_col, len(row1))
        
        # 构建地区-指标映射：{列索引: {地区, 指标信息}}
        col_region_metric_map = {}
        for region, (start_col, end_col) in regions_map.items():
            for col_idx in range(start_col, min(end_col, len(row2))):
                metric_name = row2[col_idx] if pd.notna(row2[col_idx]) else ""
                if metric_name and str(metric_name).strip():
                    metric_str = str(metric_name).strip()
                    # 标准化指标名称
                    if "出栏计划" in metric_str or "计划出栏量" in metric_str:
                        metric_key = "PROVINCE_PLAN"
                        metric_name_std = "计划出栏量"
                        unit = "头"
                    elif "实际出栏量" in metric_str:
                        metric_key = "PROVINCE_ACTUAL"
                        metric_name_std = "实际出栏量"
                        unit = "头"
                    elif "计划完成率" in metric_str or "计划达成率" in metric_str:
                        metric_key = "PROVINCE_COMPLETION_RATE"
                        metric_name_std = "计划完成率"
                        unit = "%"
                    elif "实际均重" in metric_str or ("均重" in metric_str and "计划" not in metric_str):
                        metric_key = "PROVINCE_AVG_WEIGHT"
                        metric_name_std = "均重"
                        unit = "公斤"
                    elif "计划均重" in metric_str:
                        metric_key = "PROVINCE_PLAN_WEIGHT"
                        metric_name_std = "计划均重"
                        unit = "公斤"
                    elif "销售均价" in metric_str or ("均价" in metric_str and "销售" in metric_str):
                        metric_key = "PROVINCE_PRICE"
                        metric_name_std = "销售均价"
                        unit = "元/公斤"
                    else:
                        continue
                    
                    col_region_metric_map[col_idx] = {
                        "region": region,
                        "metric_key": metric_key,
                        "metric_name": metric_name_std,
                        "unit": unit
                    }
        
        # 解析数据行（从第3行开始）
        for row_idx in range(2, len(df)):
            row = df.iloc[row_idx]
            
            # 第1列：时间类型（上旬、中旬、月度）
            period_type_str = row.iloc[0] if len(row) > 0 else None
            if pd.isna(period_type_str) or not str(period_type_str).strip():
                continue
            
            period_type_str = str(period_type_str).strip()
            
            # 第2列：日期
            date_val = None
            if len(row) > 1:
                val = row.iloc[1]
                if pd.notna(val):
                    parsed_date = parse_date(val)
                    if parsed_date:
                        date_val = parsed_date.date()
            
            if not date_val:
                continue
            
            # 解析每个列的数据
            for col_idx, metric_info in col_region_metric_map.items():
                if col_idx >= len(row):
                    continue
                
                value = row.iloc[col_idx]
                if pd.isna(value) or value == "" or value == "#N/A":
                    continue
                
                # 清理数值
                cleaned_result = clean_numeric_value_enhanced(value)
                if cleaned_result is None or cleaned_result[0] is None:
                    continue
                cleaned_value, raw_value = cleaned_result
                
                # 构建tags
                tags = {
                    "region": metric_info["region"],
                    "period_type": period_type_str  # 上旬、中旬、月度
                }
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_config.get("sheet_name", ""),
                    metric_key=metric_info["metric_key"],
                    geo_key=metric_info["region"],
                    obs_date=date_val,
                    period_end=None,
                    tags=tags
                )
                
                # 构建observation字典
                obs = {
                    "obs_date": date_val,
                    "metric_name": metric_info["metric_name"],
                    "metric_key": metric_info["metric_key"],
                    "value": cleaned_value,
                    "unit": metric_info.get("unit"),
                    "tags": tags,
                    "geo_code": metric_info["region"],
                    "period_type": "day",  # 虽然是旬度，但日期是具体的，所以用day
                    "raw_value": raw_value if raw_value else (str(value) if value else None),
                    "dedup_key": dedup_key
                }
                observations.append(obs)
        
        return observations
