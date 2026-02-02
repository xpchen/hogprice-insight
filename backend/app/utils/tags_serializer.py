import json
import hashlib
from typing import Dict, Optional, Any


# 关键tags列表（用于去重和过滤）
KEY_TAGS = [
    "pig_type",      # 猪种：标猪/外三元/商品猪...
    "weight_range",  # 体重段：110-125kg...
    "price_type",    # 价格类型：均价/报价...
    "pair",          # 价差对：河南-山东...
    "ma",            # 移动平均：7d/30d...
    "window"         # 窗口：7/30...
]


def normalize_tags_json(tags: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    标准化tags_json，只保留关键tags，并保证顺序一致
    
    Args:
        tags: 原始tags字典
    
    Returns:
        标准化后的tags字典
    """
    if not tags:
        return {}
    
    normalized = {}
    
    # 只保留关键tags
    for key in KEY_TAGS:
        if key in tags and tags[key] is not None:
            value = tags[key]
            
            # 值标准化
            if isinstance(value, str):
                # 去除首尾空格，统一大小写（小写）
                value = value.strip().lower()
                # 统一范围符号：—/～ -> -
                if key == "weight_range" or key == "pair":
                    value = value.replace("—", "-").replace("～", "-")
                # 统一kg大小写
                if "kg" in value:
                    value = value.replace("KG", "kg").replace("Kg", "kg")
            
            # 空字符串转为None
            if value == "":
                continue
                
            normalized[key] = value
    
    return normalized


def generate_tags_hash(tags: Optional[Dict[str, Any]]) -> str:
    """
    生成tags的稳定hash值（用于dedup_key）
    
    Args:
        tags: tags字典
    
    Returns:
        MD5 hash字符串（32字符）
    """
    normalized = normalize_tags_json(tags)
    
    if not normalized:
        return "0" * 32  # 空tags返回全0
    
    # 按key排序后序列化（保证顺序一致）
    sorted_items = sorted(normalized.items())
    tags_str = json.dumps(sorted_items, ensure_ascii=False, sort_keys=False)
    
    # 生成MD5 hash
    return hashlib.md5(tags_str.encode('utf-8')).hexdigest()


def generate_dedup_key(
    metric_id: int,
    obs_date: str,  # YYYY-MM-DD格式
    geo_id: Optional[int] = None,
    company_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    tags_hash: Optional[str] = None
) -> str:
    """
    生成去重键（dedup_key）
    
    Args:
        metric_id: 指标ID
        obs_date: 观测日期（YYYY-MM-DD）
        geo_id: 地区ID（可选）
        company_id: 企业ID（可选）
        warehouse_id: 交割库ID（可选）
        tags_hash: tags的hash值（可选）
    
    Returns:
        MD5 hash字符串（32字符）
    """
    components = [
        str(metric_id),
        obs_date,
        str(geo_id or 0),
        str(company_id or 0),
        str(warehouse_id or 0),
        tags_hash or ("0" * 32)
    ]
    
    # 拼接并生成hash
    key_str = "|".join(components)
    return hashlib.md5(key_str.encode('utf-8')).hexdigest()
