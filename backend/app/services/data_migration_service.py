"""数据迁移服务：从fact_observation迁移到fact_indicator_ts"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import FactObservation, DimMetric, FactIndicatorTs, DimIndicator, DimRegion, DimGeo
from app.models.metric_code_map import resolve_metric_id
from app.utils.region_normalizer import normalize_province_name
from app.services.region_mapping_service import get_or_create_region, resolve_region_code


def migrate_observations_to_indicators(
    db: Session,
    batch_size: int = 1000,
    dry_run: bool = False
) -> Dict:
    """
    从fact_observation迁移到fact_indicator_ts
    
    Args:
        db: 数据库会话
        batch_size: 批次大小
        dry_run: 是否只是预览（不实际迁移）
    
    Returns:
        {
            "total_observations": int,
            "migrated": int,
            "failed": int,
            "errors": List[str]
        }
    """
    errors = []
    migrated_count = 0
    failed_count = 0
    
    # 查询所有observation记录
    total_count = db.query(FactObservation).count()
    
    # 分批处理
    offset = 0
    while offset < total_count:
        observations = db.query(FactObservation).offset(offset).limit(batch_size).all()
        
        if not observations:
            break
        
        for obs in observations:
            try:
                # 获取metric信息
                metric = db.query(DimMetric).filter(DimMetric.id == obs.metric_id).first()
                if not metric:
                    failed_count += 1
                    errors.append(f"Observation {obs.id}: metric不存在")
                    continue
                
                # 解析indicator_code（基于metric_code_map）
                # 这里简化处理，实际需要根据raw_header解析
                indicator_code = _parse_indicator_code_from_metric(metric)
                if not indicator_code:
                    failed_count += 1
                    errors.append(f"Observation {obs.id}: 无法解析indicator_code")
                    continue
                
                # 获取或创建indicator维度
                indicator = db.query(DimIndicator).filter(
                    DimIndicator.indicator_code == indicator_code
                ).first()
                
                if not indicator:
                    indicator = DimIndicator(
                        indicator_code=indicator_code,
                        indicator_name=metric.metric_name,
                        freq=metric.freq,
                        unit=metric.unit,
                        topic=_infer_topic(metric.metric_group),
                        source_code="LEGACY",
                        calc_method="RAW"
                    )
                    db.add(indicator)
                    db.flush()
                
                # 解析region_code
                region_code = "NATION"  # 默认全国
                if obs.geo_id:
                    geo = db.query(DimGeo).filter(DimGeo.id == obs.geo_id).first()
                    if geo:
                        # 使用统一的区域映射服务
                        region = get_or_create_region(db, region_name=geo.province)
                        region_code = region.region_code
                
                # 创建fact_indicator_ts记录
                if not dry_run:
                    # 检查是否已存在
                    existing = None
                    if metric.freq == "daily":
                        existing = db.query(FactIndicatorTs).filter(
                            FactIndicatorTs.indicator_code == indicator_code,
                            FactIndicatorTs.region_code == region_code,
                            FactIndicatorTs.freq == "D",
                            FactIndicatorTs.trade_date == obs.obs_date
                        ).first()
                    else:
                        # 周频需要week_end，这里简化处理
                        existing = None
                    
                    if not existing:
                        if metric.freq == "daily":
                            new_record = FactIndicatorTs(
                                indicator_code=indicator_code,
                                region_code=region_code,
                                freq="D",
                                trade_date=obs.obs_date,
                                value=obs.value,
                                source_code="LEGACY",
                                ingest_batch_id=obs.batch_id
                            )
                        else:
                            # 周频：需要week_start和week_end，这里简化处理
                            new_record = FactIndicatorTs(
                                indicator_code=indicator_code,
                                region_code=region_code,
                                freq="W",
                                week_end=obs.obs_date,  # 简化：使用obs_date作为week_end
                                value=obs.value,
                                source_code="LEGACY",
                                ingest_batch_id=obs.batch_id
                            )
                        
                        db.add(new_record)
                        migrated_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Observation {obs.id}: {str(e)}")
                continue
        
        if not dry_run:
            db.commit()
        
        offset += batch_size
    
    return {
        "total_observations": total_count,
        "migrated": migrated_count,
        "failed": failed_count,
        "errors": errors[:100]  # 最多返回100个错误
    }


def _parse_indicator_code_from_metric(metric: DimMetric) -> Optional[str]:
    """
    从dim_metric解析indicator_code
    
    简化实现：基于metric_name和metric_group生成indicator_code
    实际应该使用metric_code_map.py的逻辑
    """
    metric_name = metric.metric_name or ""
    metric_group = metric.metric_group or ""
    
    # 简单的映射规则
    if "出栏" in metric_name and "均价" in metric_name:
        if metric_group == "province":
            return "hog_price_province"
        else:
            return "hog_price_nation"
    elif "屠宰" in metric_name:
        return "slaughter_daily"
    elif "价差" in metric_name:
        if "标肥" in metric_name:
            return "spread_std_fat"
        elif "毛白" in metric_name:
            return "spread_hog_carcass"
        else:
            return "spread_region"
    elif "利润" in metric_name:
        return "profit_breeding"
    elif "均重" in metric_name or "体重" in metric_name:
        return "hog_weight_out_week"
    elif "冻品" in metric_name or "库存" in metric_name:
        return "frozen_capacity_rate"
    elif "饲料" in metric_name or "全价料" in metric_name:
        return "feed_price_full"
    
    # 默认：使用metric_name转换为code格式
    code = metric_name.lower().replace(" ", "_").replace("（", "").replace("）", "")
    return code


def _infer_topic(metric_group: str) -> str:
    """从metric_group推断topic"""
    if metric_group == "province" or metric_group == "group" or metric_group == "warehouse":
        return "价格"
    elif "spread" in metric_group:
        return "价差"
    elif "profit" in metric_group:
        return "产业链"
    else:
        return "价格"
