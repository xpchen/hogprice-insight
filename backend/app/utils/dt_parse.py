from datetime import datetime
from typing import Optional, Any
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


def parse_period_start_end(start_value: Any, end_value: Any) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    解析周起止日期（period_start/period_end）
    
    Args:
        start_value: 开始日期值（可能是日期、字符串、公式如=B3-6）
        end_value: 结束日期值
    
    Returns:
        (period_start, period_end) 元组
    """
    period_start = parse_date(start_value)
    period_end = parse_date(end_value)
    
    # 如果开始日期是公式，尝试从结束日期回推
    if period_start is None and period_end is not None:
        if isinstance(start_value, str) and start_value.startswith('='):
            # 尝试提取数字（如=B3-6中的6）
            import re
            match = re.search(r'-(\d+)', start_value)
            if match:
                days_back = int(match.group(1))
                from datetime import timedelta
                period_start = period_end - timedelta(days=days_back)
    
    return period_start, period_end


def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """
    从文件名提取日期
    
    支持的格式：
    - 2026年2月2日涌益咨询日度数据.xlsx
    - 2026.1.16-2026.1.22涌益咨询 周度数据.xlsx
    - 2026-02-02_data.xlsx
    
    Args:
        filename: 文件名
    
    Returns:
        解析出的日期（如果是日期范围，返回结束日期）
    """
    import re
    
    # 中文日期格式：2026年2月2日
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', filename)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            return datetime(year, month, day)
        except:
            pass
    
    # 日期范围格式：2026.1.16-2026.1.22
    match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})-(\d{4})\.(\d{1,2})\.(\d{1,2})', filename)
    if match:
        # 返回结束日期
        year, month, day = int(match.group(4)), int(match.group(5)), int(match.group(6))
        try:
            return datetime(year, month, day)
        except:
            pass
    
    # 标准日期格式：2026-02-02
    match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', filename)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            return datetime(year, month, day)
        except:
            pass
    
    return None


def normalize_date(value) -> Optional[str]:
    """将日期标准化为YYYY-MM-DD格式字符串"""
    dt = parse_date(value)
    if dt:
        return dt.strftime("%Y-%m-%d")
    return None
