"""指标抽取服务 - 从fact_observation抽取核心指标到fact_indicator_ts"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import re
import json
from pathlib import Path

from app.models.fact_observation import FactObservation
from app.models.fact_observation_tag import FactObservationTag
from app.models.fact_indicator_ts import FactIndicatorTs
from app.models.dim_indicator import DimIndicator
from app.models.dim_region import DimRegion
from app.services.region_mapping_service import get_or_create_region


def load_extraction_rules() -> List[Dict[str, Any]]:
    """加载指标抽取规则配置"""
    config_path = Path(__file__).parent.parent / "config" / "indicator_extraction_rules.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("rules", [])
    return []


def get_or_create_indicator(
    db: Session,
    indicator_code: str,
    indicator_name: str,
    source_code: str,
    freq: str,
    topic: str,
    unit: Optional[str] = None
) -> DimIndicator:
    """
    获取或创建DimIndicator
    
    Args:
        db: 数据库会话
        indicator_code: 指标代码
        indicator_name: 指标名称
        source_code: 数据源代码
        freq: 频率（D/W）
        topic: 主题分类
        unit: 单位
    
    Returns:
        DimIndicator对象
    """
    indicator = db.query(DimIndicator).filter(
        DimIndicator.indicator_code == indicator_code
    ).first()
    
    if indicator:
        return indicator
    
    indicator = DimIndicator(
        indicator_code=indicator_code,
        indicator_name=indicator_name,
        freq=freq,
        unit=unit,
        topic=topic,
        source_code=source_code,
        calc_method="DERIVED"
    )
    
    db.add(indicator)
    db.flush()
    
    return indicator


def match_observation_to_rule(
    obs: FactObservation,
    rule: Dict[str, Any]
) -> bool:
    """
    检查observation是否匹配抽取规则
    
    Args:
        obs: FactObservation对象
        rule: 抽取规则
    
    Returns:
        是否匹配
    """
    conditions = rule.get("conditions", {})
    
    # 检查metric_key_pattern
    metric_key_pattern = conditions.get("metric_key_pattern")
    if metric_key_pattern:
        # 需要从metric获取metric_name或raw_header
        metric_name = obs.metric.metric_name if obs.metric else ""
        if not re.match(metric_key_pattern, metric_name):
            return False
    
    # 检查tags
    tags_conditions = conditions.get("tags", {})
    if tags_conditions:
        obs_tags = obs.tags_json or {}
        for tag_key, tag_value in tags_conditions.items():
            if tag_key not in obs_tags or obs_tags[tag_key] != tag_value:
                return False
    
    # 检查geo_code
    geo_code_condition = conditions.get("geo_code")
    if geo_code_condition:
        # 需要从geo获取province
        geo_province = obs.geo.province if obs.geo else None
        if geo_province != geo_code_condition:
            return False
    
    geo_code_pattern = conditions.get("geo_code_pattern")
    if geo_code_pattern:
        geo_province = obs.geo.province if obs.geo else "NATION"
        if not re.match(geo_code_pattern, geo_province):
            return False
    
    # 检查period_type
    period_type_condition = conditions.get("period_type")
    if period_type_condition:
        if obs.period_type != period_type_condition:
            return False
    
    return True


def extract_core_indicators(
    db: Session,
    batch_id: Optional[int] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None
) -> Dict[str, int]:
    """
    从fact_observation抽取核心指标到fact_indicator_ts
    
    Args:
        db: 数据库会话
        batch_id: 批次ID（可选，如果提供则只处理该批次）
        date_start: 开始日期（可选）
        date_end: 结束日期（可选）
    
    Returns:
        {
            "extracted": int,
            "updated": int,
            "errors": int
        }
    """
    extracted_count = 0
    updated_count = 0
    error_count = 0
    
    # 加载抽取规则
    rules = load_extraction_rules()
    
    if not rules:
        return {
            "extracted": 0,
            "updated": 0,
            "errors": 0
        }
    
    # 构建查询
    query = db.query(FactObservation).join(FactObservation.metric)
    
    if batch_id:
        query = query.filter(FactObservation.batch_id == batch_id)
    
    if date_start:
        query = query.filter(FactObservation.obs_date >= date_start)
    
    if date_end:
        query = query.filter(FactObservation.obs_date <= date_end)
    
    observations = query.all()
    
    # 按规则分组处理
    for rule in rules:
        indicator_code = rule.get("indicator_code")
        indicator_name = rule.get("indicator_name")
        source_code = rule.get("source_code")
        freq = rule.get("freq", "D")
        topic = rule.get("topic")
        unit = rule.get("unit")
        agg_method = rule.get("agg_method", "mean")
        group_by = rule.get("group_by")
        
        # 获取或创建indicator
        indicator = get_or_create_indicator(
            db=db,
            indicator_code=indicator_code,
            indicator_name=indicator_name,
            source_code=source_code,
            freq=freq,
            topic=topic,
            unit=unit
        )
        
        # 筛选匹配的observations
        matched_obs = [obs for obs in observations if match_observation_to_rule(obs, rule)]
        
        if not matched_obs:
            continue
        
        # 按group_by分组聚合
        if group_by == "geo_code":
            # 按省份分组
            grouped = {}
            for obs in matched_obs:
                region_code = obs.geo.province if obs.geo else "NATION"
                if region_code not in grouped:
                    grouped[region_code] = []
                grouped[region_code].append(obs)
            
            # 处理每个分组
            for region_code, obs_list in grouped.items():
                # 获取或创建region
                region = db.query(DimRegion).filter(DimRegion.region_code == region_code).first()
                if not region:
                    # 创建region（简化处理）
                    region = DimRegion(region_code=region_code, region_name=region_code)
                    db.add(region)
                    db.flush()
                
                # 聚合值
                values = [obs.value for obs in obs_list if obs.value is not None]
                if not values:
                    continue
                
                if agg_method == "mean":
                    agg_value = sum(values) / len(values)
                elif agg_method == "sum":
                    agg_value = sum(values)
                elif agg_method == "max":
                    agg_value = max(values)
                elif agg_method == "min":
                    agg_value = min(values)
                else:
                    agg_value = values[0]  # 默认取第一个
                
                # 确定日期键
                if freq == "D":
                    date_key = obs_list[0].obs_date
                    week_start = None
                    week_end = None
                else:
                    date_key = obs_list[0].period_end
                    week_start = obs_list[0].period_start
                    week_end = obs_list[0].period_end
                
                if not date_key:
                    continue
                
                # 查找或创建fact_indicator_ts
                existing = db.query(FactIndicatorTs).filter(
                    and_(
                        FactIndicatorTs.indicator_code == indicator_code,
                        FactIndicatorTs.region_code == region_code,
                        FactIndicatorTs.freq == freq,
                        FactIndicatorTs.trade_date == date_key if freq == "D" else FactIndicatorTs.week_end == date_key
                    )
                ).first()
                
                if existing:
                    existing.value = agg_value
                    updated_count += 1
                else:
                    new_ts = FactIndicatorTs(
                        indicator_code=indicator_code,
                        region_code=region_code,
                        freq=freq,
                        trade_date=date_key if freq == "D" else None,
                        week_start=week_start,
                        week_end=week_end if freq == "W" else None,
                        value=agg_value
                    )
                    db.add(new_ts)
                    extracted_count += 1
        
        else:
            # 不分组，直接聚合
            values = [obs.value for obs in matched_obs if obs.value is not None]
            if not values:
                continue
            
            if agg_method == "mean":
                agg_value = sum(values) / len(values)
            elif agg_method == "sum":
                agg_value = sum(values)
            else:
                agg_value = values[0]
            
            # 使用NATION作为region_code
            region_code = "NATION"
            # 使用统一的区域映射服务
            region = get_or_create_region(db, region_code=region_code)
            
            # 确定日期键
            if freq == "D":
                date_key = matched_obs[0].obs_date
                week_start = None
                week_end = None
            else:
                date_key = matched_obs[0].period_end
                week_start = matched_obs[0].period_start
                week_end = matched_obs[0].period_end
            
            if not date_key:
                continue
            
            # 查找或创建fact_indicator_ts
            existing = db.query(FactIndicatorTs).filter(
                and_(
                    FactIndicatorTs.indicator_code == indicator_code,
                    FactIndicatorTs.region_code == region_code,
                    FactIndicatorTs.freq == freq,
                    FactIndicatorTs.trade_date == date_key if freq == "D" else FactIndicatorTs.week_end == date_key
                )
            ).first()
            
            if existing:
                existing.value = agg_value
                updated_count += 1
            else:
                new_ts = FactIndicatorTs(
                    indicator_code=indicator_code,
                    region_code=region_code,
                    freq=freq,
                    trade_date=date_key if freq == "D" else None,
                    week_start=week_start,
                    week_end=week_end if freq == "W" else None,
                    value=agg_value
                )
                db.add(new_ts)
                extracted_count += 1
    
    # 提交
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        error_count = extracted_count + updated_count
        extracted_count = 0
        updated_count = 0
    
    return {
        "extracted": extracted_count,
        "updated": updated_count,
        "errors": error_count
    }
