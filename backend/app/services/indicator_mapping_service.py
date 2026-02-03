"""指标映射服务"""
import json
import os
from typing import Dict, Optional
from pathlib import Path
from app.utils.region_normalizer import normalize_province_name


# 加载映射配置
_mapping_config = None


def _load_mapping_config():
    """加载指标映射配置"""
    global _mapping_config
    if _mapping_config is None:
        config_path = Path(__file__).parent.parent / "data" / "indicator_mappings.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            _mapping_config = json.load(f)
    return _mapping_config


def resolve_indicator_code(
    sheet_name: str,
    field_name: str,
    region: Optional[str] = None
) -> Optional[str]:
    """
    解析指标代码
    
    Args:
        sheet_name: Sheet名称
        field_name: 字段名称
        region: 区域名称（可选，用于替换模板中的{province}/{region}）
    
    Returns:
        指标代码，如果找不到映射则返回None
    """
    config = _load_mapping_config()
    
    # 查找匹配的映射规则
    for mapping in config.get("mappings", []):
        if mapping.get("sheet_name") != sheet_name:
            continue
        
        mapping_field = mapping.get("field_name", "")
        
        # 支持通配符 "*"
        if mapping_field == "*" or mapping_field == field_name:
            indicator_code = mapping.get("indicator_code")
            
            # 如果indicator_code包含占位符，需要根据region替换
            if region and "{province}" in indicator_code:
                normalized_region = normalize_province_name(region)
                indicator_code = indicator_code.replace("{province}", normalized_region.lower().replace(" ", "_"))
            elif region and "{region}" in indicator_code:
                # 区域映射（大区）
                region_mappings = config.get("region_mappings", {})
                region_code = None
                for code, name in region_mappings.items():
                    if name == region:
                        region_code = code.lower()
                        break
                if region_code:
                    indicator_code = indicator_code.replace("{region}", region_code)
            
            return indicator_code
    
    return None


def resolve_region_code(province_name: str) -> str:
    """
    标准化省份名称并返回region_code
    
    注意：此函数已废弃，请使用 app.services.region_mapping_service.resolve_region_code
    保留此函数是为了向后兼容
    
    Args:
        province_name: 省份名称
    
    Returns:
        标准化的region_code
    """
    # 使用统一的区域映射服务
    from app.services.region_mapping_service import resolve_region_code as _resolve_region_code
    return _resolve_region_code(province_name)


def get_indicator_config(indicator_code: str) -> Optional[Dict]:
    """
    获取指标的完整配置信息
    
    Args:
        indicator_code: 指标代码
    
    Returns:
        指标配置字典，包含freq, unit, topic等信息
    """
    config = _load_mapping_config()
    
    for mapping in config.get("mappings", []):
        if mapping.get("indicator_code") == indicator_code:
            return {
                "indicator_code": indicator_code,
                "indicator_name": mapping.get("indicator_name", indicator_code),
                "freq": mapping.get("freq", "D"),
                "unit": mapping.get("unit"),
                "topic": mapping.get("topic"),
                "region_code": mapping.get("region_code"),
                "sub_key": mapping.get("sub_key")
            }
    
    return None
