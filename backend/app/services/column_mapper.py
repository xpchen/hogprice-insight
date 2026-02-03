"""列映射转换器 - 将ObservationDict转换为表记录格式"""
from typing import List, Dict, Any, Optional
from datetime import date
from app.services.ingestors.parsers.base_parser import ObservationDict
from app.utils.region_normalizer import normalize_province_name
from app.utils.value_cleaner import clean_numeric_value


class ColumnMapper:
    """列映射转换器"""
    
    def __init__(self):
        self.normalizers = {
            "normalize_province_name": normalize_province_name,
        }
        self.cleaners = {
            "clean_numeric_value": clean_numeric_value,
        }
    
    def map_observations_to_table_records(
        self,
        observations: List[ObservationDict],
        column_mapping: Dict[str, Any],
        table_name: str,
        batch_id: int,
        sheet_config: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """
        将ObservationDict转换为表记录格式
        
        Args:
            observations: 观测值字典列表
            column_mapping: 列映射配置
            table_name: 目标表名
            batch_id: 批次ID
        
        Returns:
            表记录列表
        """
        # 对于某些表，需要将多个observation合并为一条记录
        # 例如：价格+宰量表，需要将3个metric合并为一条记录
        
        # 检查是否需要合并记录（多个observation合并为一条）
        # 如果unique_key只包含日期/周期字段，且存在多个value字段，则需要合并
        unique_key_fields = []
        value_fields = []
        for col_name, mapping_config in column_mapping.items():
            source = mapping_config.get("source")
            # 识别唯一键字段：日期、周期、行维度、标签等
            if source in ["date_col", "period_start", "period_end", "row_dim.province", "tags.indicator", "tags.province", "subheader"]:
                unique_key_fields.append(col_name)
            elif source == "value":
                value_fields.append(col_name)
        
        # 如果需要合并（有多个value字段）
        # 检查unique_key配置，如果有多个value字段，通常需要合并
        need_merge = len(value_fields) > 1
        
        if need_merge:
            # 按唯一键分组
            grouped = {}
            
            for obs in observations:
                # 构建分组键
                group_key_parts = []
                for col_name in unique_key_fields:
                    mapping_config = column_mapping[col_name]
                    value = self._extract_value(obs, mapping_config, sheet_config)
                    if value:
                        group_key_parts.append(str(value))
                
                group_key = "|".join(group_key_parts) if group_key_parts else str(obs.get("obs_date") or obs.get("period_end"))
                
                if group_key not in grouped:
                    grouped[group_key] = {"batch_id": batch_id}
                    # 初始化所有唯一键字段
                    for col_name in unique_key_fields:
                        mapping_config = column_mapping[col_name]
                        value = self._extract_value(obs, mapping_config, sheet_config)
                        if value is not None:
                            value = self._apply_transforms(value, mapping_config)
                            grouped[group_key][col_name] = value
                
                # 提取value字段（根据condition过滤）
                for col_name in value_fields:
                    mapping_config = column_mapping[col_name]
                    value = self._extract_value(obs, mapping_config, sheet_config)
                    if value is not None:
                        value = self._apply_transforms(value, mapping_config)
                        grouped[group_key][col_name] = value
            
            return list(grouped.values())
        else:
            # 不需要合并，直接转换
            records = []
            
            for obs in observations:
                record = {"batch_id": batch_id}
                
                # 遍历列映射配置
                for column_name, mapping_config in column_mapping.items():
                    value = self._extract_value(obs, mapping_config, sheet_config)
                    
                    # 应用转换规则
                    if value is not None:
                        value = self._apply_transforms(value, mapping_config)
                    
                    record[column_name] = value
                
                records.append(record)
            
            return records
    
    def _extract_value(self, obs: ObservationDict, mapping_config: Dict[str, Any], sheet_config: Optional[Dict[str, Any]] = None) -> Any:
        """从observation中提取值"""
        source = mapping_config.get("source")
        
        if source == "date_col":
            return obs.get("obs_date")
        
        elif source == "period_start":
            return obs.get("period_start")
        
        elif source == "period_end":
            return obs.get("period_end")
        
        elif source == "row_dim.date":
            # 从行维度获取日期（对于钢联数据，日期在第一列）
            return obs.get("obs_date") or obs.get("period_end")
        
        elif source == "row_dim.province":
            # 从geo_code获取省份（这是parser设置的）
            geo_code = obs.get("geo_code")
            if geo_code:
                # 标准化省份名称
                normalizer = mapping_config.get("normalizer")
                if normalizer and normalizer in self.normalizers:
                    normalized = self.normalizers[normalizer](geo_code)
                    # 调试：如果标准化后仍然是"指标"，说明geo_code本身就是错误的
                    if normalized == "指标" or geo_code == "指标":
                        # 尝试从tags中获取province
                        tags = obs.get("tags", {})
                        province_from_tags = tags.get("province")
                        if province_from_tags and province_from_tags != "指标":
                            if normalizer:
                                return self.normalizers[normalizer](province_from_tags)
                            return province_from_tags
                    return normalized
                return geo_code
            return None
        
        elif source == "column_name":
            # 从列名提取（需要从tags或metric_key中获取）
            # 对于钢联数据，列名信息在raw_header或tags中
            tags = obs.get("tags", {})
            # 优先使用顶层的column_name，然后是tags中的column_name或raw_header，最后是metric_name
            raw_header = obs.get("column_name") or tags.get("column_name") or tags.get("raw_header") or obs.get("metric_name") or ""
            
            # 如果有extract_pattern，使用正则提取
            extract_pattern = mapping_config.get("extract_pattern")
            if extract_pattern and raw_header:
                import re
                match = re.search(extract_pattern, raw_header)
                if match:
                    # 返回第一个捕获组，如果没有捕获组则返回整个匹配
                    if match.groups():
                        extracted_value = match.group(1)
                        # 应用normalizer（如果有）
                        normalizer = mapping_config.get("normalizer")
                        if normalizer and normalizer in self.normalizers:
                            extracted_value = self.normalizers[normalizer](extracted_value)
                        return extracted_value
                    return match.group(0)
            
            # 如果没有pattern，直接返回raw_header（需要进一步处理）
            # 如果配置了normalizer，也应用一下
            normalizer = mapping_config.get("normalizer")
            if normalizer and normalizer in self.normalizers and raw_header:
                return self.normalizers[normalizer](raw_header)
            return raw_header
        
        elif source == "subheader":
            # 从tags中提取subheader对应的值
            tags = obs.get("tags", {})
            # 根据condition过滤
            condition = mapping_config.get("condition")
            if condition:
                # 简单的条件判断，如 "subheader in [规模场, 小散户, 均价]"
                if "subheader in" in condition:
                    # 提取允许的subheader列表
                    import re
                    match = re.search(r'\[(.*?)\]', condition)
                    if match:
                        allowed = [s.strip() for s in match.group(1).split(',')]
                        # 检查tags中的scale或stat是否匹配
                        scale = tags.get("scale", "")
                        if scale in allowed:
                            return scale
                elif "subheader ==" in condition or "subheader =" in condition:
                    # 提取目标值
                    target = condition.split("=")[-1].strip().strip('"').strip("'")
                    stat = tags.get("stat", "")
                    if stat == target:
                        return stat
            
            # 默认从tags中提取scale或stat
            return tags.get("scale") or tags.get("stat")
        
        elif source == "value":
            # 根据condition过滤
            condition = mapping_config.get("condition")
            if condition:
                tags = obs.get("tags", {})
                metric_key = obs.get("metric_key", "")
                
                # 检查metric_key条件
                if "metric_key ==" in condition or "metric_key == " in condition:
                    # 支持 "metric_key == YY_W_SLAUGHTER_PRELIVE_WEIGHT" 格式
                    parts = condition.split("==")
                    if len(parts) == 2:
                        target = parts[1].strip().strip('"').strip("'")
                        if metric_key != target:
                            return None
                    else:
                        # 尝试其他格式
                        target = condition.split("==")[-1].strip().strip('"').strip("'")
                        if metric_key != target:
                            return None
                
                # 检查subheader条件
                elif "subheader in" in condition:
                    import re
                    match = re.search(r'\[(.*?)\]', condition)
                    if match:
                        allowed = [s.strip().strip('"').strip("'") for s in match.group(1).split(',')]
                        scale = tags.get("scale", "")
                        if scale not in allowed:
                            return None
                elif "subheader ==" in condition or "subheader =" in condition:
                    target = condition.split("=")[-1].strip().strip('"').strip("'")
                    stat = tags.get("stat", "")
                    if stat != target:
                        return None
            
            return obs.get("value")
        
        elif source.startswith("meta."):
            # 从tags中提取meta字段
            meta_key = source.replace("meta.", "")
            tags = obs.get("tags", {})
            
            # 特殊处理：meta.unit_row, meta.update_time_row等
            if meta_key == "unit_row":
                # 从unit字段获取
                return obs.get("unit")
            elif meta_key == "update_time_row":
                # 从tags中获取updated_at_time
                return tags.get("updated_at_time")
            elif meta_key == "province_row":
                # 从geo_code获取
                return obs.get("geo_code")
            elif meta_key.startswith("premium_row_"):
                # 从tags中获取升贴水信息
                return tags.get(meta_key)
            elif meta_key == "weight_row":
                # 从tags中获取weight_band
                return tags.get("weight_band")
            
            return tags.get(meta_key)
        
        elif source.startswith("tags."):
            # 从tags中提取字段
            tag_key = source.replace("tags.", "")
            tags = obs.get("tags", {})
            return tags.get(tag_key)
        
        return None
    
    def _apply_transforms(self, value: Any, mapping_config: Dict[str, Any]) -> Any:
        """应用转换规则"""
        # 值映射
        value_map = mapping_config.get("value_map")
        if value_map and value in value_map:
            value = value_map[value]
        
        # 数据清洗
        cleaner = mapping_config.get("cleaner")
        if cleaner and cleaner in self.cleaners:
            value = self.cleaners[cleaner](value)
        
        # 标准化
        normalizer = mapping_config.get("normalizer")
        if normalizer and normalizer in self.normalizers:
            value = self.normalizers[normalizer](value)
        
        return value
