"""Observation Upserter - 幂等写入fact_observation，同时写入fact_observation_tag"""
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError

from app.models.fact_observation import FactObservation
from app.models.fact_observation_tag import FactObservationTag
from app.models.dim_metric import DimMetric
from app.models.dim_geo import DimGeo
from app.services.ingestors.parsers.base_parser import ObservationDict


def get_or_create_metric(
    db: Session,
    metric_key: str,
    metric_name: str,
    sheet_name: str,
    unit: Optional[str] = None,
    freq: str = "D"
) -> DimMetric:
    """
    根据metric_key获取或创建DimMetric
    
    Args:
        db: 数据库会话
        metric_key: 指标键
        metric_name: 指标名称
        sheet_name: sheet名称
        unit: 单位
        freq: 频率（D/W）
    
    Returns:
        DimMetric对象
    """
    # 尝试查找现有metric（基于raw_header和sheet_name）
    # 注意：metric_name可能是raw_header（完整列名），需要精确匹配
    metric = db.query(DimMetric).filter(
        and_(
            DimMetric.raw_header == metric_name,
            DimMetric.sheet_name == sheet_name
        )
    ).first()
    
    # 如果没找到，尝试通过metric_key查找（如果metric_key不为空）
    if not metric and metric_key:
        metric = db.query(DimMetric).filter(
            and_(
                DimMetric.sheet_name == sheet_name,
                func.json_unquote(
                    func.json_extract(DimMetric.parse_json, '$.metric_key')
                ) == metric_key
            )
        ).first()
    
    if metric:
        # 如果metric已存在，确保parse_json中包含metric_key
        if not metric.parse_json:
            metric.parse_json = {}
        # 只有当metric_key不为空时才更新
        if metric_key and metric.parse_json.get("metric_key") != metric_key:
            metric.parse_json["metric_key"] = metric_key
            db.flush()
        # 如果metric_key为空但parse_json中也没有metric_key，记录警告
        elif not metric_key and not metric.parse_json.get("metric_key"):
            print(f"      ⚠️  警告: metric_key为空，无法设置到parse_json！metric_name={metric_name}, sheet_name={sheet_name}", flush=True)
        return metric
    
    # 创建新metric
    # 根据metric_key推断metric_group
    metric_group = "province"  # 默认
    if "SLAUGHTER" in metric_key:
        metric_group = "warehouse"
    elif "SPREAD" in metric_key or "价差" in metric_name:
        metric_group = "spread"
    elif "PROFIT" in metric_key or "利润" in metric_name:
        metric_group = "profit"
    
    # 构建parse_json，确保包含metric_key（只有当metric_key不为空时）
    parse_json = {}
    if metric_key:
        parse_json["metric_key"] = metric_key
    else:
        print(f"      ⚠️  警告: 创建metric时metric_key为空！metric_name={metric_name}, sheet_name={sheet_name}", flush=True)
    
    # 对于毛白价差sheet，metric_name可能是完整的raw_header
    # 需要确保raw_header正确设置
    raw_header_value = metric_name  # 使用metric_name作为raw_header
    
    metric = DimMetric(
        metric_group=metric_group,
        metric_name=metric_name,
        unit=unit,
        freq=freq,
        raw_header=raw_header_value,  # 使用metric_name（可能是raw_header）
        sheet_name=sheet_name,
        parse_json=parse_json if parse_json else None
    )
    
    db.add(metric)
    db.flush()
    
    return metric


def get_or_create_geo(
    db: Session,
    geo_code: Optional[str]
) -> Optional[int]:
    """
    根据geo_code获取geo_id
    
    Args:
        db: 数据库会话
        geo_code: 地理位置代码（省份名或NATION）
    
    Returns:
        geo_id或None
    """
    if not geo_code or geo_code == "NATION":
        return None
    
    # 查找DimGeo
    geo = db.query(DimGeo).filter(DimGeo.province == geo_code).first()
    if geo:
        return geo.id
    
    # 如果不存在，创建（简化处理，实际可能需要更复杂的逻辑）
    # 这里先返回None，后续可以扩展
    return None


def upsert_observations(
    db: Session,
    observations: List[ObservationDict],
    batch_id: int,
    sheet_name: str = ""
) -> Dict[str, int]:
    """
    批量upsert observations到fact_observation，同时写入tags
    
    Args:
        db: 数据库会话
        observations: 观测值字典列表
        batch_id: 导入批次ID
        sheet_name: sheet名称（用于创建metric）
    
    Returns:
        {
            "inserted": int,
            "updated": int,
            "errors": int
        }
    """
    inserted_count = 0
    updated_count = 0
    error_count = 0
    
    # 批量获取或创建metrics（避免N+1查询）
    metric_cache = {}
    geo_cache = {}
    
    for i, obs in enumerate(observations):
        try:
            metric_key = obs.get("metric_key", "")
            metric_name = obs.get("metric_name", metric_key)
            
            # 如果metric_key为空，使用metric_name作为缓存key
            cache_key = metric_key if metric_key else f"{sheet_name}::{metric_name}"
            
            # 获取或创建metric
            if cache_key not in metric_cache:
                metric = get_or_create_metric(
                    db=db,
                    metric_key=metric_key,
                    metric_name=metric_name,
                    sheet_name=sheet_name,
                    unit=obs.get("unit"),
                    freq=obs.get("period_type", "day")[0].upper()  # D/W
                )
                metric_cache[cache_key] = metric.id
            metric_id = metric_cache[cache_key]
            
            # 获取geo_id
            geo_code = obs.get("geo_code")
            geo_id = None
            if geo_code:
                if geo_code not in geo_cache:
                    geo_id_val = get_or_create_geo(db, geo_code)
                    geo_cache[geo_code] = geo_id_val
                geo_id = geo_cache[geo_code]
            
            # 查找现有observation（基于dedup_key）
            dedup_key = obs.get("dedup_key")
            if not dedup_key:
                error_count += 1
                continue
            
            existing = db.query(FactObservation).filter(
                FactObservation.dedup_key == dedup_key
            ).first()
            
            if existing:
                # 插入优先模式：有重复则跳过，不做更新
                continue
            else:
                # 创建新记录
                new_obs = FactObservation(
                    batch_id=batch_id,
                    metric_id=metric_id,
                    obs_date=obs.get("obs_date"),
                    period_type=obs.get("period_type"),
                    period_start=obs.get("period_start"),
                    period_end=obs.get("period_end"),
                    value=obs.get("value"),
                    raw_value=obs.get("raw_value"),
                    geo_id=geo_id,
                    tags_json=obs.get("tags", {}),
                    dedup_key=dedup_key
                )
                
                db.add(new_obs)
                
                # 立即flush，检查是否有错误（如唯一键冲突）
                try:
                    db.flush()  # 获取id
                except IntegrityError as flush_error:
                    # 插入优先模式：dedup_key冲突视为重复，跳过不更新
                    db.rollback()
                    continue
                except Exception as flush_error:
                    db.rollback()
                    error_count += 1
                    if error_count <= 10:
                        print(f"      ⚠️  错误 #{error_count}: 插入记录时flush失败 - {type(flush_error).__name__}: {str(flush_error)[:300]}", flush=True)
                        print(f"         metric_key={metric_key}, geo_code={geo_code}, obs_date={obs.get('obs_date')}", flush=True)
                        import traceback
                        print(f"         详细堆栈: {traceback.format_exc()[:500]}", flush=True)
                    continue
                
                # 写入tags
                tags = obs.get("tags", {})
                for tag_key, tag_value in tags.items():
                    if tag_value is not None:  # 跳过None值
                        tag = FactObservationTag(
                            observation_id=new_obs.id,
                            tag_key=str(tag_key),
                            tag_value=str(tag_value)
                        )
                        db.add(tag)
                
                inserted_count += 1
        
        except IntegrityError as e:
            db.rollback()
            error_count += 1
            # 记录前几个错误的详细信息（用于调试）
            if error_count <= 10:  # 增加到10个错误
                print(f"      ⚠️  错误 #{error_count}: IntegrityError - {str(e)[:300]}", flush=True)
                print(f"         metric_key={obs.get('metric_key')}, geo_code={obs.get('geo_code')}, dedup_key={obs.get('dedup_key')[:50] if obs.get('dedup_key') else None}", flush=True)
                print(f"         obs_date={obs.get('obs_date')}, period_end={obs.get('period_end')}, value={obs.get('value')}", flush=True)
            continue
        except Exception as e:
            db.rollback()
            error_count += 1
            # 记录前几个错误的详细信息（用于调试）
            if error_count <= 10:  # 增加到10个错误
                print(f"      ⚠️  错误 #{error_count}: {type(e).__name__} - {str(e)[:300]}", flush=True)
                print(f"         metric_key={obs.get('metric_key')}, geo_code={obs.get('geo_code')}, obs_date={obs.get('obs_date')}", flush=True)
                import traceback
                print(f"         详细堆栈: {traceback.format_exc()[:800]}", flush=True)
            continue
    
    # 批量提交（所有记录都已经flush了，这里只是commit）
    try:
        db.commit()
        print(f"      ✓ 批量提交成功: 插入={inserted_count}, 更新={updated_count}, 错误={error_count}", flush=True)
    except IntegrityError as e:
        db.rollback()
        # 可能是dedup_key冲突，需要重新处理
        print(f"      ⚠️  批量提交时IntegrityError: {str(e)[:300]}", flush=True)
        print(f"         尝试逐条处理冲突的记录...", flush=True)
        
        # 重置计数器
        inserted_count = 0
        updated_count = 0
        
        # 逐条处理，处理冲突
        for obs in observations:
            try:
                metric_key = obs.get("metric_key", "")
                metric_name = obs.get("metric_name", metric_key)
                cache_key = metric_key if metric_key else f"{sheet_name}::{metric_name}"
                
                if cache_key not in metric_cache:
                    metric = get_or_create_metric(
                        db=db,
                        metric_key=metric_key,
                        metric_name=metric_name,
                        sheet_name=sheet_name,
                        unit=obs.get("unit"),
                        freq=obs.get("period_type", "day")[0].upper()
                    )
                    metric_cache[cache_key] = metric.id
                metric_id = metric_cache[cache_key]
                
                geo_code = obs.get("geo_code")
                geo_id = None
                if geo_code:
                    if geo_code not in geo_cache:
                        geo_id_val = get_or_create_geo(db, geo_code)
                        geo_cache[geo_code] = geo_id_val
                    geo_id = geo_cache[geo_code]
                
                dedup_key = obs.get("dedup_key")
                if not dedup_key:
                    error_count += 1
                    continue
                
                existing = db.query(FactObservation).filter(
                    FactObservation.dedup_key == dedup_key
                ).first()
                
                if existing:
                    # 插入优先模式：有重复则跳过
                    continue
                else:
                    # 插入
                    new_obs = FactObservation(
                        batch_id=batch_id,
                        metric_id=metric_id,
                        obs_date=obs.get("obs_date"),
                        period_type=obs.get("period_type"),
                        period_start=obs.get("period_start"),
                        period_end=obs.get("period_end"),
                        value=obs.get("value"),
                        raw_value=obs.get("raw_value"),
                        geo_id=geo_id,
                        tags_json=obs.get("tags", {}),
                        dedup_key=dedup_key
                    )
                    db.add(new_obs)
                    db.flush()
                    
                    tags = obs.get("tags", {})
                    for tag_key, tag_value in tags.items():
                        if tag_value is not None:
                            tag = FactObservationTag(
                                observation_id=new_obs.id,
                                tag_key=str(tag_key),
                                tag_value=str(tag_value)
                            )
                            db.add(tag)
                    
                    inserted_count += 1
                    
            except Exception as e2:
                db.rollback()
                error_count += 1
                if error_count <= 10:
                    print(f"      ⚠️  错误 #{error_count}: {type(e2).__name__} - {str(e2)[:200]}", flush=True)
                continue
        
        try:
            db.commit()
            print(f"      ✓ 逐条处理后提交成功: 插入={inserted_count}, 更新={updated_count}", flush=True)
        except Exception as e3:
            db.rollback()
            print(f"      ❌ 逐条处理后仍然失败: {type(e3).__name__} - {str(e3)[:300]}", flush=True)
            error_count += len(observations) - inserted_count - updated_count
            
    except Exception as e:
        db.rollback()
        print(f"      ❌ 批量提交失败: {type(e).__name__} - {str(e)[:300]}", flush=True)
        import traceback
        print(f"         详细堆栈: {traceback.format_exc()[:500]}", flush=True)
        # 如果批量提交失败，所有记录都失败了
        error_count += inserted_count + updated_count
        inserted_count = 0
        updated_count = 0
    
    return {
        "inserted": inserted_count,
        "updated": updated_count,
        "errors": error_count
    }
