"""
P9解析器：白条市场跟踪数据
处理两种格式：
1. "白条市场"sheet：日期列 + 多列（到货量/价格对）
2. "华宝和牧原白条"sheet：日期列 + 多列（华宝、牧原、区域）
"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import pandas as pd
import re
from openpyxl.worksheet.worksheet import Worksheet

from .base_parser import BaseParser, ObservationDict
from app.utils.dt_parse import parse_date
from app.utils.value_cleaner import clean_numeric_value_enhanced


class P9WhiteStripMarketParser(BaseParser):
    """P9解析器：处理白条市场跟踪数据"""
    
    def parse(
        self,
        sheet_data: Any,
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析白条市场数据
        """
        observations = []
        
        # 转换为DataFrame
        if isinstance(sheet_data, Worksheet):
            data = list(sheet_data.values)
            df = pd.DataFrame(data)
        elif isinstance(sheet_data, pd.DataFrame):
            df = sheet_data
        else:
            df = pd.read_excel(sheet_data, engine='openpyxl', header=None)
        
        if df.empty:
            return observations
        
        # 获取配置
        header_config = sheet_config.get("header", {})
        header_row = header_config.get("header_row", 0)
        sub_header_row = header_config.get("sub_header_row")  # 可选：第二行表头（如 华宝和牧原白条 sheet 下 华东、河南山东 等）
        metrics_config = sheet_config.get("metrics_from_columns", [])
        sheet_name = sheet_config.get("sheet_name", "")
        
        # 获取表头
        if header_row >= len(df):
            return observations
        
        headers = df.iloc[header_row].tolist()
        # 每列使用的表头文本：优先第二行表头（非空时），否则用第一行，用于多表头 Excel（如 牧原白条 下 华东、河南山东 等）
        header_per_col = []
        sub_row = df.iloc[sub_header_row] if (sub_header_row is not None and sub_header_row < len(df)) else None
        for col_idx in range(len(headers)):
            prim = headers[col_idx] if col_idx < len(headers) else None
            sub = sub_row.iloc[col_idx] if sub_row is not None and col_idx < len(sub_row) else None
            prim_str = str(prim).strip() if prim is not None and pd.notna(prim) and str(prim).strip() else ""
            sub_str = str(sub).strip() if sub is not None and pd.notna(sub) and str(sub).strip() else ""
            header_per_col.append(sub_str if sub_str else prim_str)
        
        # 查找日期列
        date_col_idx = None
        for idx, header in enumerate(headers):
            if header and isinstance(header, str) and '日期' in str(header):
                date_col_idx = idx
                break
        
        if date_col_idx is None:
            return observations
        
        # 构建列名到指标的映射（每列只映射一个指标；多表头时用 header_per_col 匹配）
        column_metric_map = {}
        for metric_config in metrics_config:
            pattern = metric_config.get("column_pattern", "")
            if not pattern:
                continue
            
            # 查找匹配的列：先在第一行表头找，再在合并后的 header_per_col 找（避免重复占用同一列）
            for col_idx, col_name in enumerate(header_per_col):
                if col_idx in column_metric_map:
                    continue
                if col_name and pattern in col_name:
                    column_metric_map[col_idx] = {
                        "metric_key": metric_config.get("metric_key"),
                        "metric_name": metric_config.get("metric_name"),
                        "unit": metric_config.get("unit"),
                        "tags": metric_config.get("tags", {}),
                        "metric_group": metric_config.get("metric_group", "white_strip")
                    }
                    break
            else:
                # 若 header_per_col 未匹配到，再试仅第一行表头（兼容单行表头）
                for col_idx, col_name in enumerate(headers):
                    if col_idx in column_metric_map:
                        continue
                    if col_name and isinstance(col_name, str) and pattern in str(col_name):
                        column_metric_map[col_idx] = {
                            "metric_key": metric_config.get("metric_key"),
                            "metric_name": metric_config.get("metric_name"),
                            "unit": metric_config.get("unit"),
                            "tags": metric_config.get("tags", {}),
                            "metric_group": metric_config.get("metric_group", "white_strip")
                        }
                        break
        
        # 解析数据行
        for row_idx in range(header_row + 1, len(df)):
            row = df.iloc[row_idx]
            
            # 获取日期
            date_val = row.iloc[date_col_idx] if date_col_idx < len(row) else None
            if not date_val or pd.isna(date_val):
                continue
            
            # 解析日期
            obs_date = self._parse_date_value(date_val)
            if not obs_date:
                continue
            
            # 处理每个指标列
            for col_idx, metric_info in column_metric_map.items():
                if col_idx >= len(row):
                    continue
                
                value = row.iloc[col_idx]
                if pd.isna(value):
                    continue
                
                # 清理数值（处理"~"符号、范围值等）
                cleaned_value = self._clean_value(value)
                if cleaned_value is None:
                    continue
                
                # 构建tags
                tags = metric_info["tags"].copy()
                
                # 生成dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code=source_code,
                    sheet_name=sheet_name,
                    metric_key=metric_info["metric_key"],
                    geo_key=None,
                    obs_date=obs_date,
                    period_end=None,
                    tags=tags
                )
                
                observations.append({
                    "metric_key": metric_info["metric_key"],
                    "metric_name": metric_info["metric_name"],
                    "obs_date": obs_date,
                    "period_type": profile_defaults.get("period_type", "day"),
                    "value": cleaned_value,
                    "unit": metric_info.get("unit"),
                    "tags": tags,
                    "dedup_key": dedup_key,
                    "batch_id": batch_id,
                    "source_code": source_code
                })
        
        return observations
    
    def _parse_date_value(self, date_val: Any) -> Optional[date]:
        """解析日期值"""
        if isinstance(date_val, date):
            return date_val
        elif isinstance(date_val, datetime):
            return date_val.date()
        elif isinstance(date_val, str):
            # 处理格式：2025.12.19
            try:
                # 替换点为横杠
                date_str = date_val.replace('.', '-')
                # 尝试解析
                parts = date_str.split('-')
                if len(parts) == 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    return date(year, month, day)
            except:
                pass
            
            # 尝试标准格式
            try:
                return datetime.strptime(date_val, '%Y-%m-%d').date()
            except:
                pass
        elif isinstance(date_val, (int, float)):
            # Excel日期序列号
            try:
                excel_epoch = datetime(1899, 12, 30)
                return (excel_epoch + timedelta(days=int(date_val))).date()
            except:
                pass
        
        return None
    
    def _clean_value(self, value: Any) -> Optional[float]:
        """清理数值，处理"~"符号、范围值等"""
        if pd.isna(value):
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # 移除"~"符号
            value = value.replace('~', '').strip()
            
            # 处理范围值，如"13.0 - 15.2"，取平均值
            if ' - ' in value or '-' in value:
                parts = re.split(r'\s*-\s*', value)
                try:
                    nums = [float(p.strip()) for p in parts if p.strip()]
                    if nums:
                        return sum(nums) / len(nums)
                except:
                    pass
            
            # 处理多个值，如"14.4-14.2-14.0"，取平均值
            if '-' in value and not value.startswith('-'):
                parts = value.split('-')
                try:
                    nums = [float(p.strip()) for p in parts if p.strip() and p.strip()[0].isdigit()]
                    if nums:
                        return sum(nums) / len(nums)
                except:
                    pass
            
            # 处理特殊标记，如"(昨降)"、"(涨200)"等
            if '(' in value or '（' in value:
                # 提取数字部分
                match = re.search(r'[\d.]+', value)
                if match:
                    try:
                        return float(match.group())
                    except:
                        pass
                return None
            
            # 尝试直接转换为浮点数
            try:
                return float(value)
            except:
                pass
        
        return None
