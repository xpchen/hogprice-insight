"""维度抽取工具 - 从列名/行名提取tags（scale, weight_band, mode, sentiment, city等）"""
from typing import Dict, Any, Optional
import re


# 关键词映射表
SCALE_KEYWORDS = {
    "规模场": "规模场",
    "规模": "规模场",
    "小散": "小散",
    "散户": "小散",
    "均价": "均价",
    "平均": "均价"
}

WEIGHT_BAND_KEYWORDS = {
    r"(\d+)-(\d+)kg": lambda m: f"{m.group(1)}-{m.group(2)}kg",
    r"(\d+)kg": lambda m: f"{m.group(1)}kg",
    "标猪": "标猪",
    "肥猪": "肥猪"
}

MODE_KEYWORDS = {
    "自繁自养": "自繁自养",
    "外购": "外购",
    "外购仔猪": "外购"
}

SENTIMENT_KEYWORDS = {
    "平稳": "平稳",
    "放缓": "放缓",
    "加快": "加快",
    "积极": "积极",
    "谨慎": "谨慎"
}


def extract_tags_from_text(text: str) -> Dict[str, str]:
    """
    从文本中提取tags
    
    Args:
        text: 文本（列名或行名）
    
    Returns:
        tags字典
    """
    if not text or not isinstance(text, str):
        return {}
    
    text = text.strip()
    tags = {}
    
    # 提取scale
    for keyword, value in SCALE_KEYWORDS.items():
        if keyword in text:
            tags["scale"] = value
            break
    
    # 提取weight_band
    for pattern, handler in WEIGHT_BAND_KEYWORDS.items():
        if isinstance(handler, str):
            if handler in text:
                tags["weight_band"] = handler
                break
        else:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tags["weight_band"] = handler(match)
                break
    
    # 提取mode
    for keyword, value in MODE_KEYWORDS.items():
        if keyword in text:
            tags["mode"] = value
            break
    
    # 提取sentiment
    for keyword, value in SENTIMENT_KEYWORDS.items():
        if keyword in text:
            tags["sentiment"] = value
            break
    
    # 提取城市（简单匹配，后续可扩展）
    city_match = re.search(r'([^省]+[市县])', text)
    if city_match:
        city = city_match.group(1)
        if len(city) <= 10:  # 避免误匹配
            tags["city"] = city
    
    return tags


def extract_tags_from_column_name(col_name: str, sheet_config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    从列名提取tags（考虑sheet配置）
    
    Args:
        col_name: 列名
        sheet_config: sheet配置（可能包含metric_template的tags）
    
    Returns:
        tags字典
    """
    tags = {}
    
    # 从sheet配置获取默认tags
    if sheet_config:
        metric_template = sheet_config.get("metric_template", {})
        if metric_template:
            template_tags = metric_template.get("tags", {})
            tags.update(template_tags)
    
    # 从列名提取tags
    col_tags = extract_tags_from_text(col_name)
    tags.update(col_tags)
    
    return tags


def extract_tags_from_row_name(row_name: str, sheet_config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    从行名提取tags
    
    Args:
        row_name: 行名
        sheet_config: sheet配置
    
    Returns:
        tags字典
    """
    return extract_tags_from_text(row_name)
