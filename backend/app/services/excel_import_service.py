import hashlib
import pandas as pd
from io import BytesIO
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.models import (
    ImportBatch, DimMetric, DimGeo, DimCompany, DimWarehouse, FactObservation
)
from app.services.metric_parse_service import parse_header
from app.utils.dt_parse import parse_date, normalize_date
from app.utils.tags_serializer import normalize_tags_json, generate_tags_hash, generate_dedup_key


def calculate_file_hash(file_content: bytes) -> str:
    """计算文件hash"""
    return hashlib.sha256(file_content).hexdigest()


def clean_value(value) -> Optional[float]:
    """清洗数值，将NA/空值/异常字符串转为None"""
    if pd.isna(value) or value is None:
        return None
    
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ['na', 'n/a', 'null', 'none', '', '-', '--']:
            return None
        try:
            return float(value)
        except ValueError:
            return None
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _batch_upsert_observations(db: Session, observations: List[Dict]) -> Tuple[int, int]:
    """
    批量upsert观测数据（使用dedup_key）
    
    Args:
        db: 数据库会话
        observations: 观测数据列表，每个元素包含所有字段
    
    Returns:
        (inserted_count, updated_count): 插入和更新的记录数
    """
    if not observations:
        return 0, 0
    
    # 提取所有dedup_key
    dedup_keys = [obs["dedup_key"] for obs in observations]
    
    # 查询已存在的记录
    existing_records = {
        obs.dedup_key: obs 
        for obs in db.query(FactObservation).filter(
            FactObservation.dedup_key.in_(dedup_keys)
        ).all()
    }
    
    # 分离需要插入和更新的记录
    to_insert = []
    updated_count = 0
    
    for obs_data in observations:
        dedup_key = obs_data["dedup_key"]
        if dedup_key in existing_records:
            # 更新已有记录
            existing = existing_records[dedup_key]
            existing.value = obs_data["value"]
            existing.batch_id = obs_data["batch_id"]
            existing.tags_json = obs_data["tags_json"]
            existing.raw_value = obs_data["raw_value"]
            updated_count += 1
        else:
            # 插入新记录
            to_insert.append(FactObservation(**obs_data))
    
    # 批量插入
    inserted_count = len(to_insert)
    if to_insert:
        db.bulk_save_objects(to_insert)
    
    # 更新操作已经在查询后直接修改对象，flush即可
    db.flush()
    
    return inserted_count, updated_count


def import_excel(
    db: Session,
    file_content: bytes,
    filename: str,
    uploader_id: Optional[int] = None
) -> Dict:
    """
    导入Excel文件
    
    Args:
        db: 数据库会话
        file_content: 文件内容（bytes）
        filename: 文件名
        uploader_id: 上传者ID
    
    Returns:
        {
            "batch_id": int,
            "summary": {
                "total_rows": int,
                "success_rows": int,
                "failed_rows": int,
                "sheets_processed": int
            },
            "errors": List[Dict]
        }
    """
    errors = []
    total_rows = 0
    success_rows = 0
    failed_rows = 0
    inserted_count = 0
    updated_count = 0
    metric_ids_set = set()  # 用于统计指标数量
    
    # 记录开始时间
    start_time = datetime.now()
    
    # 计算文件hash
    file_hash = calculate_file_hash(file_content)
    
    # 创建导入批次
    batch = ImportBatch(
        filename=filename,
        file_hash=file_hash,
        uploader_id=uploader_id,
        status="processing",
        total_rows=0,
        success_rows=0,
        failed_rows=0,
        sheet_count=0,
        metric_count=0,
        duration_ms=0,
        inserted_count=0,
        updated_count=0
    )
    db.add(batch)
    db.flush()  # 获取batch.id
    
    try:
        # 读取Excel文件（使用BytesIO包装bytes）
        excel_file = pd.ExcelFile(BytesIO(file_content), engine='openpyxl')
        sheet_names = excel_file.sheet_names
        
        # 处理每个sheet
        for sheet_name in sheet_names:
            try:
                # 读取sheet（不设header）
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, engine='openpyxl')
                
                if df.empty or len(df) < 5:
                    errors.append({
                        "sheet": sheet_name,
                        "row": None,
                        "col": None,
                        "reason": "Sheet数据行数不足（至少需要5行）"
                    })
                    continue
                
                # 第2行：指标名称（列定义）
                header_row = df.iloc[1]  # 索引1是第2行
                # 第3行：单位
                unit_row = df.iloc[2]  # 索引2是第3行
                # 第4行：更新时间
                updated_at_row = df.iloc[3]  # 索引3是第4行
                # 第5行起：数据
                data_df = df.iloc[4:].copy()
                
                # 第一列是日期列
                date_col = data_df.iloc[:, 0]
                
                # 处理每一列（从第2列开始，第1列是日期）
                for col_idx in range(1, len(header_row)):
                    try:
                        raw_header = str(header_row.iloc[col_idx]).strip()
                        if not raw_header or raw_header.lower() in ['nan', 'none', '']:
                            continue
                        
                        unit = str(unit_row.iloc[col_idx]) if col_idx < len(unit_row) else None
                        if unit and unit.lower() in ['nan', 'none']:
                            unit = None
                        
                        source_updated_at = str(updated_at_row.iloc[col_idx]) if col_idx < len(updated_at_row) else None
                        if source_updated_at and source_updated_at.lower() in ['nan', 'none']:
                            source_updated_at = None
                        
                        # 解析指标
                        parse_result = parse_header(raw_header, sheet_name)
                        
                        # Upsert dim_metric
                        metric = db.query(DimMetric).filter(
                            and_(
                                DimMetric.raw_header == raw_header,
                                DimMetric.sheet_name == sheet_name
                            )
                        ).first()
                        
                        if not metric:
                            metric = DimMetric(
                                metric_group=parse_result["metric_group"],
                                metric_name=parse_result["metric_name"],
                                unit=unit,
                                freq=parse_result["freq"],
                                raw_header=raw_header,
                                sheet_name=sheet_name,
                                source_updated_at=source_updated_at,
                                parse_json=parse_result,
                                # 自动填充元数据
                                value_type=parse_result.get("value_type", "price"),
                                preferred_agg=parse_result.get("preferred_agg", "mean"),
                                suggested_axis=parse_result.get("suggested_axis", "auto"),
                                seasonality_supported=parse_result.get("seasonality_supported", True)
                            )
                            db.add(metric)
                            db.flush()
                        else:
                            # 更新已有指标
                            metric.metric_group = parse_result["metric_group"]
                            metric.metric_name = parse_result["metric_name"]
                            metric.unit = unit
                            metric.freq = parse_result["freq"]
                            metric.parse_json = parse_result
                            metric.source_updated_at = source_updated_at
                            # 更新元数据（如果之前没有）
                            if not metric.value_type:
                                metric.value_type = parse_result.get("value_type", "price")
                            if not metric.preferred_agg:
                                metric.preferred_agg = parse_result.get("preferred_agg", "mean")
                            if not metric.suggested_axis:
                                metric.suggested_axis = parse_result.get("suggested_axis", "auto")
                            if not metric.seasonality_supported:
                                metric.seasonality_supported = parse_result.get("seasonality_supported", True)
                        
                        # Upsert维度表
                        geo_id = None
                        if parse_result.get("geo"):
                            geo = db.query(DimGeo).filter(DimGeo.province == parse_result["geo"]).first()
                            if not geo:
                                geo = DimGeo(
                                    province=parse_result["geo"],
                                    region=parse_result.get("region")
                                )
                                db.add(geo)
                                db.flush()
                            geo_id = geo.id
                        
                        company_id = None
                        if parse_result.get("company"):
                            company = db.query(DimCompany).filter(
                                DimCompany.company_name == parse_result["company"]
                            ).first()
                            if not company:
                                company = DimCompany(
                                    company_name=parse_result["company"],
                                    province=parse_result.get("geo")
                                )
                                db.add(company)
                                db.flush()
                            company_id = company.id
                        
                        warehouse_id = None
                        if parse_result.get("warehouse"):
                            warehouse = db.query(DimWarehouse).filter(
                                DimWarehouse.warehouse_name == parse_result["warehouse"]
                            ).first()
                            if not warehouse:
                                warehouse = DimWarehouse(
                                    warehouse_name=parse_result["warehouse"],
                                    province=parse_result.get("geo")
                                )
                                db.add(warehouse)
                                db.flush()
                            warehouse_id = warehouse.id
                        
                        # 处理数据行：批量收集
                        value_col = data_df.iloc[:, col_idx]
                        observations_batch = []  # 批量收集要插入/更新的记录
                        
                        for row_idx, (date_val, value_val) in enumerate(zip(date_col, value_col)):
                            try:
                                # 解析日期
                                obs_date = parse_date(date_val)
                                if not obs_date:
                                    errors.append({
                                        "sheet": sheet_name,
                                        "row": row_idx + 5,  # 实际行号（从1开始，加上前4行）
                                        "col": col_idx + 1,
                                        "reason": f"无法解析日期: {date_val}"
                                    })
                                    failed_rows += 1
                                    total_rows += 1
                                    continue
                                
                                # 清洗数值
                                clean_val = clean_value(value_val)
                                if clean_val is None:
                                    # 空值跳过，不记录
                                    continue
                                
                                # 准备tags_json（标准化）
                                raw_tags = parse_result.get("tags", {})
                                tags_json = normalize_tags_json(raw_tags)
                                tags_hash = generate_tags_hash(raw_tags)
                                
                                # 生成dedup_key
                                obs_date_str = obs_date.strftime("%Y-%m-%d")
                                dedup_key = generate_dedup_key(
                                    metric_id=metric.id,
                                    obs_date=obs_date_str,
                                    geo_id=geo_id,
                                    company_id=company_id,
                                    warehouse_id=warehouse_id,
                                    tags_hash=tags_hash
                                )
                                
                                # 收集到批量列表
                                observations_batch.append({
                                    "dedup_key": dedup_key,
                                    "batch_id": batch.id,
                                    "metric_id": metric.id,
                                    "obs_date": obs_date.date(),
                                    "value": clean_val,
                                    "geo_id": geo_id,
                                    "company_id": company_id,
                                    "warehouse_id": warehouse_id,
                                    "tags_json": tags_json,
                                    "raw_value": str(value_val) if isinstance(value_val, str) else None
                                })
                                
                                success_rows += 1
                                total_rows += 1
                                
                            except Exception as e:
                                errors.append({
                                    "sheet": sheet_name,
                                    "row": row_idx + 5,
                                    "col": col_idx + 1,
                                    "reason": f"处理数据行错误: {str(e)}"
                                })
                                failed_rows += 1
                                total_rows += 1
                        
                        # 批量upsert（每列处理完后）
                        if observations_batch:
                            insert_count, update_count = _batch_upsert_observations(db, observations_batch)
                            inserted_count += insert_count
                            updated_count += update_count
                            metric_ids_set.add(metric.id)
                        
                    except Exception as e:
                        errors.append({
                            "sheet": sheet_name,
                            "row": None,
                            "col": col_idx + 1,
                            "reason": f"处理列错误: {str(e)}"
                        })
                        failed_rows += 1
            
            except Exception as e:
                errors.append({
                    "sheet": sheet_name,
                    "row": None,
                    "col": None,
                    "reason": f"处理Sheet错误: {str(e)}"
                })
                failed_rows += 1
        
        # 计算耗时
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # 统计错误摘要
        error_summary = {}
        if errors:
            for error in errors:
                reason = error.get("reason", "未知错误")
                error_summary[reason] = error_summary.get(reason, 0) + 1
        
        # 更新批次状态
        batch.status = "success" if failed_rows == 0 else ("partial" if success_rows > 0 else "failed")
        batch.total_rows = total_rows
        batch.success_rows = success_rows
        batch.failed_rows = failed_rows
        batch.sheet_count = len(sheet_names)
        batch.metric_count = len(metric_ids_set)
        batch.duration_ms = duration_ms
        batch.inserted_count = inserted_count
        batch.updated_count = updated_count
        batch.error_json = {
            "errors": errors[:100] if errors else [],  # 最多保留100个详细错误
            "error_summary": error_summary  # 错误摘要
        } if errors else None
        
        db.commit()
        
        return {
            "batch_id": batch.id,
            "summary": {
                "total_rows": total_rows,
                "success_rows": success_rows,
                "failed_rows": failed_rows,
                "sheets_processed": len(sheet_names)
            },
            "errors": errors[:100]  # 最多返回100个错误
        }
    
    except Exception as e:
        db.rollback()
        batch.status = "failed"
        batch.error_json = [{"reason": f"导入失败: {str(e)}"}]
        db.commit()
        
        return {
            "batch_id": batch.id,
            "summary": {
                "total_rows": total_rows,
                "success_rows": success_rows,
                "failed_rows": failed_rows,
                "sheets_processed": 0
            },
            "errors": [{"reason": f"导入失败: {str(e)}"}]
        }
