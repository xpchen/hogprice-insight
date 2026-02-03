"""解析器基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date
import pandas as pd
from openpyxl import Workbook


# 观测值字典类型定义
ObservationDict = Dict[str, Any]
"""
观测值字典结构：
{
    "metric_key": str,  # 指标键（如 YY_D_PRICE_NATION_AVG）
    "metric_name": str,  # 指标名称
    "obs_date": date,  # 观测日期（日度）
    "period_type": Optional[str],  # day/week/month（周度/月度）
    "period_start": Optional[date],  # 周期开始日期
    "period_end": Optional[date],  # 周期结束日期
    "value": Optional[float],  # 数值
    "raw_value": Optional[str],  # 原始字符串值
    "geo_code": Optional[str],  # 地理位置代码（省份/城市）
    "tags": Dict[str, str],  # 标签字典（scale, weight_band, mode 等）
    "unit": Optional[str],  # 单位
    "dedup_key": str,  # 去重键
}
"""


class BaseParser(ABC):
    """解析器基类 - 所有解析器必须继承此类"""
    
    @abstractmethod
    def parse(
        self,
        sheet_data: Any,  # pandas DataFrame 或 openpyxl Worksheet
        sheet_config: Dict[str, Any],
        profile_defaults: Dict[str, Any],
        source_code: str,
        batch_id: int
    ) -> List[ObservationDict]:
        """
        解析 sheet 数据
        
        Args:
            sheet_data: sheet 数据（DataFrame 或 Worksheet）
            sheet_config: sheet 配置（来自 IngestProfileSheet.config_json）
            profile_defaults: profile 默认配置（来自 IngestProfile.defaults_json）
            source_code: 数据源代码
            batch_id: 导入批次ID
        
        Returns:
            观测值字典列表
        """
        pass
    
    def _generate_dedup_key(
        self,
        source_code: str,
        sheet_name: str,
        metric_key: str,
        geo_key: Optional[str],
        obs_date: Optional[date],
        period_end: Optional[date],
        tags: Dict[str, str]
    ) -> str:
        """
        生成去重键
        
        Args:
            source_code: 数据源代码
            sheet_name: sheet 名称
            metric_key: 指标键
            geo_key: 地理位置键
            obs_date: 观测日期（日度）
            period_end: 周期结束日期（周度/月度）
            tags: 标签字典
        
        Returns:
            去重键（SHA1 hash）
        """
        import hashlib
        
        # 规范化 tags（按键排序）
        canonical_tags = "|".join(
            f"{k}={v}" for k, v in sorted(tags.items())
        )
        
        # 构建键字符串
        date_key = obs_date.isoformat() if obs_date else (period_end.isoformat() if period_end else "")
        geo_key_str = geo_key or ""
        
        key_str = f"{source_code}|{sheet_name}|{metric_key}|{geo_key_str}|{date_key}|{canonical_tags}"
        
        # 生成 SHA1 hash
        return hashlib.sha1(key_str.encode('utf-8')).hexdigest()
    
    def _clean_tags(self, tags: Dict[str, Any]) -> Dict[str, str]:
        """
        清理标签字典，确保所有值都是字符串
        
        Args:
            tags: 原始标签字典
        
        Returns:
            清理后的标签字典
        """
        cleaned = {}
        for k, v in tags.items():
            if v is not None:
                cleaned[str(k)] = str(v)
        return cleaned
    
    def _merge_tags(self, *tag_dicts: Dict[str, Any]) -> Dict[str, str]:
        """
        合并多个标签字典
        
        Args:
            *tag_dicts: 多个标签字典
        
        Returns:
            合并后的标签字典
        """
        merged = {}
        for tag_dict in tag_dicts:
            if tag_dict:
                merged.update(self._clean_tags(tag_dict))
        return merged
