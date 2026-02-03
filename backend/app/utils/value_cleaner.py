"""数值清洗统一函数"""
from typing import Optional, Dict, Any
import re


def clean_numeric_value(value) -> Optional[float]:
    """
    统一处理数值清洗：去除千分位逗号、处理空值/异常字符串
    
    Args:
        value: 输入值（可能是字符串、数字、None等）
    
    Returns:
        清洗后的float值，如果无法解析则返回None
    """
    if value is None:
        return None
    
    # 如果是字符串，先去除空格并转小写
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        
        # 处理特殊空值标识
        if value.lower() in ['na', 'n/a', 'null', 'none', '', '-', '--', '——', 'nan']:
            return None
        
        # 去除千分位逗号
        value = value.replace(',', '')
        
        # 尝试转换为float
        try:
            return float(value)
        except ValueError:
            return None
    
    # 如果是数字类型，直接转换
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_interval_value(value: str) -> Dict[str, Any]:
    """
    解析区间字符串（如"15.5-16.5"）
    
    Args:
        value: 区间字符串
    
    Returns:
        {
            "min": float,
            "max": float,
            "raw": str
        } 或 None（如果无法解析）
    """
    import re
    
    if not isinstance(value, str):
        return None
    
    value = value.strip()
    
    # 匹配区间格式：15.5-16.5 或 15.5~16.5 或 15.5—16.5
    match = re.match(r'([\d.]+)\s*[-~—]\s*([\d.]+)', value)
    if match:
        try:
            min_val = float(match.group(1))
            max_val = float(match.group(2))
            return {
                "min": min_val,
                "max": max_val,
                "raw": value
            }
        except ValueError:
            pass
    
    return None


def parse_value_with_unit(value: str) -> Dict[str, Any]:
    """
    解析带单位的数值（如"15.5元/公斤"）
    
    Args:
        value: 带单位的字符串
    
    Returns:
        {
            "value": float,
            "unit": str,
            "raw": str
        } 或 None（如果无法解析）
    """
    import re
    
    if not isinstance(value, str):
        return None
    
    value = value.strip()
    
    # 排除非数值字符串（如"90kg以下"、"150kg以上"等）
    # 这些应该作为indicator值，而不是数值
    if value.endswith("以下") or value.endswith("以上") or value.endswith("以下") or value.endswith("以上"):
        return None
    
    # 匹配数值+单位格式
    match = re.match(r'([\d.,]+)\s*(.+)', value)
    if match:
        try:
            num_str = match.group(1).replace(',', '')
            num_value = float(num_str)
            unit = match.group(2).strip()
            # 如果单位包含"以下"或"以上"，说明这不是一个有效的数值+单位格式
            if "以下" in unit or "以上" in unit:
                return None
            return {
                "value": num_value,
                "unit": unit,
                "raw": value
            }
        except ValueError:
            pass
    
    return None


def clean_numeric_value_enhanced(value) -> tuple[Optional[float], Optional[str]]:
    """
    增强的数值清洗：支持区间字符串、带单位数值
    
    Args:
        value: 输入值
    
    Returns:
        (numeric_value, raw_value) 元组
        - numeric_value: 清洗后的数值（如果是区间，返回平均值；如果无法解析返回None）
        - raw_value: 原始字符串（保留用于后续处理）
    """
    if value is None:
        return None, None
    
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None, None
        
        # 处理特殊空值标识
        if value.lower() in ['na', 'n/a', 'null', 'none', '', '-', '--', '——', 'nan']:
            return None, value
        
        # 尝试解析区间
        interval = parse_interval_value(value)
        if interval:
            # 返回平均值
            avg = (interval["min"] + interval["max"]) / 2
            return avg, interval["raw"]
        
        # 尝试解析带单位数值
        value_with_unit = parse_value_with_unit(value)
        if value_with_unit:
            return value_with_unit["value"], value_with_unit["raw"]
        
        # 普通数值清洗
        numeric = clean_numeric_value(value)
        return numeric, value if numeric is None else None
    
    # 数字类型
    try:
        return float(value), None
    except (ValueError, TypeError):
        return None, str(value)
