"""质量规则验证器 - 验证observation数据的完整性和正确性"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import date
from app.services.ingestors.parsers.base_parser import ObservationDict
from app.services.ingestors.error_collector import ErrorCollector


class ObservationValidator:
    """Observation数据验证器"""
    
    def __init__(self, error_collector: ErrorCollector):
        """
        初始化验证器
        
        Args:
            error_collector: 错误收集器
        """
        self.error_collector = error_collector
    
    def validate_observation(
        self,
        obs: ObservationDict,
        sheet_name: str,
        row_no: Optional[int] = None,
        skip_metric_key_check: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        验证单个observation
        
        Args:
            obs: 观测值字典
            sheet_name: sheet名称
            row_no: 行号（可选）
            skip_metric_key_check: 是否跳过metric_key检查（用于新架构独立表）
        
        Returns:
            (is_valid, error_message) 元组
        """
        # 1. 必填字段检查（新架构独立表不需要metric_key）
        if not skip_metric_key_check and not obs.get("metric_key"):
            self.error_collector.record_missing_required(
                field_name="metric_key",
                sheet_name=sheet_name,
                row_no=row_no
            )
            return False, "metric_key缺失"
        
        # 2. 日期/周期检查
        obs_date = obs.get("obs_date")
        period_end = obs.get("period_end")
        period_type = obs.get("period_type", "day")
        
        if period_type == "day":
            if not obs_date:
                self.error_collector.record_missing_required(
                    field_name="obs_date",
                    sheet_name=sheet_name,
                    row_no=row_no
                )
                return False, "obs_date缺失（日度数据）"
        else:
            if not period_end:
                self.error_collector.record_missing_required(
                    field_name="period_end",
                    sheet_name=sheet_name,
                    row_no=row_no
                )
                return False, "period_end缺失（周度/月度数据）"
        
        # 3. 数值检查
        value = obs.get("value")
        raw_value = obs.get("raw_value")
        
        if value is None and raw_value is None:
            # 非数值处理：记录warning但不阻断
            self.error_collector.record_invalid_value(
                field_name="value",
                value=None,
                reason="数值和原始值都为空",
                sheet_name=sheet_name,
                row_no=row_no
            )
            # 不阻断，允许继续（可能是文本数据）
        
        # 4. 异常范围检查（warning级别）
        if value is not None:
            # 价格范围检查（示例：0-100元/公斤）
            if "PRICE" in obs.get("metric_key", ""):
                if value < 0 or value > 100:
                    self.error_collector.record_out_of_range(
                        field_name="value",
                        value=value,
                        valid_range="0-100",
                        sheet_name=sheet_name,
                        row_no=row_no
                    )
                    # 不阻断，只记录warning
            
            # 屠宰量范围检查（示例：0-1000000头）
            if "SLAUGHTER" in obs.get("metric_key", ""):
                if value < 0 or value > 1000000:
                    self.error_collector.record_out_of_range(
                        field_name="value",
                        value=value,
                        valid_range="0-1000000",
                        sheet_name=sheet_name,
                        row_no=row_no
                    )
        
        # 5. dedup_key检查（新架构独立表不需要dedup_key）
        if not skip_metric_key_check and not obs.get("dedup_key"):
            self.error_collector.record_missing_required(
                field_name="dedup_key",
                sheet_name=sheet_name,
                row_no=row_no
            )
            return False, "dedup_key缺失"
        
        return True, None
    
    def validate_batch(
        self,
        observations: List[ObservationDict],
        sheet_name: str,
        skip_metric_key_check: bool = False
    ) -> List[ObservationDict]:
        """
        批量验证observations
        
        Args:
            observations: 观测值字典列表
            sheet_name: sheet名称
        
        Returns:
            验证通过的观测值列表
        """
        valid_observations = []
        
        for idx, obs in enumerate(observations, start=1):
            is_valid, error_msg = self.validate_observation(
                obs=obs,
                sheet_name=sheet_name,
                row_no=idx,
                skip_metric_key_check=skip_metric_key_check
            )
            
            if is_valid:
                valid_observations.append(obs)
        
        return valid_observations
