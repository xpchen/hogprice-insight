"""区域标准化工具"""
from typing import Dict, Optional


# 省份别名映射表
PROVINCE_ALIASES: Dict[str, str] = {
    "内蒙": "内蒙古",
    "内蒙古自治区": "内蒙古",
    "新疆维吾尔自治区": "新疆",
    "新疆自治区": "新疆",
    "西藏自治区": "西藏",
    "宁夏回族自治区": "宁夏",
    "宁夏自治区": "宁夏",
    "广西壮族自治区": "广西",
    "广西自治区": "广西",
    "香港特别行政区": "香港",
    "澳门特别行政区": "澳门",
    "台湾省": "台湾",
    "台湾": "台湾",
}


def normalize_province_name(name: str) -> str:
    """
    标准化省份名称（处理别名）
    
    Args:
        name: 原始省份名称
    
    Returns:
        标准化后的省份名称
    """
    if not name:
        return name
    
    name = name.strip()
    
    # 检查别名映射
    if name in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[name]
    
    # 如果包含"省"、"市"、"自治区"等后缀，去除
    name = name.replace("省", "").replace("市", "").replace("自治区", "").replace("特别行政区", "")
    
    return name.strip()
