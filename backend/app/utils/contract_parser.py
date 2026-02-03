"""合约解析工具"""
import re
from typing import Dict, Optional


def parse_futures_contract(contract_code: str) -> Dict:
    """
    解析期货合约代码
    
    Args:
        contract_code: 合约代码，如 "lh2603"
    
    Returns:
        {
            "instrument": "LH",
            "year": 2026,
            "month": 3,
            "contract_code": "lh2603"
        }
    """
    if not contract_code:
        raise ValueError("合约代码不能为空")
    
    # 匹配模式：lh2603 -> instrument=lh, year=26, month=03
    # 假设格式：品种代码(2-3字母) + 年份(2位) + 月份(2位)
    match = re.match(r'^([a-z]+)(\d{2})(\d{2})$', contract_code.lower())
    if not match:
        raise ValueError(f"无法解析合约代码格式: {contract_code}")
    
    instrument_code = match.group(1).upper()
    year_suffix = int(match.group(2))
    month = int(match.group(3))
    
    # 年份处理：26 -> 2026, 25 -> 2025
    # 假设年份范围在2000-2099
    year = 2000 + year_suffix
    
    return {
        "instrument": instrument_code,
        "year": year,
        "month": month,
        "contract_code": contract_code
    }


def parse_option_contract(option_code: str) -> Dict:
    """
    解析期权合约代码
    
    Args:
        option_code: 期权代码，如 "lh2603-C-10000"
    
    Returns:
        {
            "underlying_contract": "lh2603",
            "option_type": "C",
            "strike": 10000.0,
            "option_code": "lh2603-C-10000"
        }
    """
    if not option_code:
        raise ValueError("期权代码不能为空")
    
    # 匹配模式：lh2603-C-10000 -> underlying=lh2603, type=C, strike=10000
    # 格式：标的合约-类型-行权价
    # 支持大小写，标的合约可以是2-3个字母+4位数字
    option_code_upper = option_code.upper()
    match = re.match(r'^([A-Z]+\d{4})-([CP])-(\d+(?:\.\d+)?)$', option_code_upper)
    if not match:
        raise ValueError(f"无法解析期权代码格式: {option_code}")
    
    underlying = match.group(1).lower()  # 转换为小写存储
    option_type = match.group(2)  # C或P
    strike = float(match.group(3))
    
    return {
        "underlying_contract": underlying,
        "option_type": option_type,
        "strike": strike,
        "option_code": option_code.lower()  # 统一转换为小写
    }
