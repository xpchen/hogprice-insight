from datetime import datetime
from typing import Optional
import pandas as pd
import re


def parse_date(value) -> Optional[datetime]:
    """
    解析日期，支持多种格式
    
    支持的格式：
    - YYYY/MM/DD
    - YYYY-MM-DD
    - Excel serial number
    - datetime对象
    """
    if pd.isna(value) or value is None:
        return None
    
    # 如果是datetime对象
    if isinstance(value, datetime):
        return value
    
    # 如果是pandas Timestamp
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    
    # 如果是字符串
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() in ['na', 'n/a', 'null', 'none', '']:
            return None
        
        # 尝试常见格式
        formats = [
            "%Y/%m/%d",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y年%m月%d日",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    
    # 如果是数字（可能是Excel serial number）
    try:
        if isinstance(value, (int, float)):
            # Excel日期从1900-01-01开始
            return pd.Timestamp('1900-01-01') + pd.Timedelta(days=int(value) - 2)
    except:
        pass
    
    return None


def normalize_date(value) -> Optional[str]:
    """将日期标准化为YYYY-MM-DD格式字符串"""
    dt = parse_date(value)
    if dt:
        return dt.strftime("%Y-%m-%d")
    return None
