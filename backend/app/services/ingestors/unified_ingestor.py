"""统一导入工作流 - 整合Raw层、Dispatcher、Parser、Validator、Upsert、Extractor"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from openpyxl import load_workbook
from io import BytesIO
import hashlib

from app.models.import_batch import ImportBatch
from app.services.ingestors.raw_writer import (
    save_raw_file, save_all_sheets_from_workbook, update_sheet_parse_status
)
from app.services.ingestors.dispatcher import create_dispatcher, Dispatcher
from app.services.ingestors.error_collector import ErrorCollector
from app.services.ingestors.parsers import get_parser, PARSER_REGISTRY
from app.services.ingestors.profile_loader import get_profile_by_dataset_type
from app.services.ingestors.observation_upserter import upsert_observations
from app.services.ingestors.validator import ObservationValidator


def unified_import(
    db: Session,
    file_content: bytes,
    filename: str,
    uploader_id: int,
    dataset_type: str,
    source_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    统一导入工作流
    
    工作流：
    1. 创建import_batch
    2. 保存raw_file（文件名、hash、日期范围）
    3. 读取workbook，遍历每个sheet：
       - 保存raw_sheet + raw_table
       - Dispatcher分派parser
       - 调用对应parser解析
       - 验证数据（validate）
       - 幂等upsert到fact_observation
       - 记录错误到ingest_error
    4. 触发指标抽取（extract_indicators）
    5. 更新batch状态
    
    Args:
        db: 数据库会话
        file_content: 文件内容（bytes）
        filename: 文件名
        uploader_id: 上传者ID
        dataset_type: 数据集类型（YONGYI_DAILY/YONGYI_WEEKLY/GANGLIAN_DAILY等）
        source_code: 数据源代码（可选，从dataset_type推断）
    
    Returns:
        导入结果字典
    """
    start_time = datetime.now()
    errors = []
    inserted_count = 0
    updated_count = 0
    error_count = 0
    total_sheets = 0
    parsed_sheets = 0
    batch = None
    
    try:
        # 1. 创建import_batch
        file_hash = hashlib.sha256(file_content).hexdigest()
        batch = ImportBatch(
            filename=filename,
            file_hash=file_hash,
            uploader_id=uploader_id,
            status="processing",
            source_code=source_code or dataset_type,
            total_rows=0,
            success_rows=0,
            failed_rows=0
        )
        db.add(batch)
        db.flush()
        batch_id = batch.id
        
        # 2. 保存raw_file
        raw_file = save_raw_file(
            db=db,
            batch_id=batch_id,
            filename=filename,
            file_content=file_content
        )
        
        # 3. 加载profile和创建dispatcher
        profile = get_profile_by_dataset_type(db, dataset_type)
        if not profile:
            # 尝试自动加载配置文件
            print(f"  ⚠️  Profile不存在，尝试自动加载...", flush=True)
            from app.services.ingestors.profile_loader import load_profile_from_json
            from pathlib import Path
            import os
            
            # 查找配置文件
            script_dir = Path(__file__).parent.parent.parent
            project_root = script_dir.parent if script_dir.name == 'app' else script_dir
            docs_dir = project_root / 'docs'
            
            profile_file_map = {
                'YONGYI_WEEKLY': 'ingest_profile_yongyi_weekly_v1.json',
                'YONGYI_DAILY': 'ingest_profile_yongyi_daily_v1.json',
                'GANGLIAN_DAILY': 'ingest_profile_ganglian_daily_v1.json',
                'ENTERPRISE_DAILY': 'ingest_profile_enterprise_daily_v1.json'
            }
            
            profile_file = profile_file_map.get(dataset_type)
            if profile_file:
                json_path = docs_dir / profile_file
                if json_path.exists():
                    try:
                        profile = load_profile_from_json(db, str(json_path))
                        print(f"  ✓ 成功加载Profile: {profile.profile_code} ({len(profile.sheets)} sheets)", flush=True)
                    except Exception as e:
                        print(f"  ❌ 加载Profile失败: {e}", flush=True)
                        raise ValueError(f"未找到profile且自动加载失败: dataset_type={dataset_type}, error={e}")
                else:
                    raise ValueError(f"未找到profile且配置文件不存在: {json_path}")
            else:
                raise ValueError(f"未找到profile: dataset_type={dataset_type}")
        
        if not profile.sheets or len(profile.sheets) == 0:
            raise ValueError(f"Profile存在但sheets配置为空: profile_code={profile.profile_code}")
        
        print(f"  ✓ Profile已加载: {profile.profile_code} ({len(profile.sheets)} sheets)", flush=True)
        
        dispatcher = Dispatcher(db, profile)
        error_collector = ErrorCollector(db, batch_id)
        
        # 4. 读取workbook并保存所有sheet到raw层
        workbook = load_workbook(BytesIO(file_content), data_only=True)
        # 使用sparse格式和限制行数来优化存储
        # 对于超大sheet，save_raw_table会自动跳过存储（只保留元信息）
        raw_sheets = save_all_sheets_from_workbook(
            db=db,
            raw_file_id=raw_file.id,
            workbook_or_path=workbook,
            sparse=True,  # 使用稀疏格式
            max_rows=None  # None表示由save_raw_table根据sheet大小自动决定
        )
        total_sheets = len(raw_sheets)
        
        # 5. 遍历每个sheet进行处理
        for sheet_idx, raw_sheet in enumerate(raw_sheets, 1):
            sheet_name = raw_sheet.sheet_name
            
            # 记录sheet处理开始（强制刷新输出）
            print(f"\n  📄 处理Sheet [{sheet_idx}/{total_sheets}]: {sheet_name}", flush=True)
            print(f"     └─ 开始时间: {datetime.now().strftime('%H:%M:%S')}", flush=True)
            
            # 导入前：获取目标表的记录数（如果有table_config）
            table_name = None
            table_config = None
            count_before = None
            if raw_sheet.parse_status == "parsed":
                # 尝试获取sheet_config以确定目标表
                try:
                    sheet_config = dispatcher.get_sheet_config(sheet_name)
                    if sheet_config:
                        table_config = sheet_config.get("table_config")
                        if table_config:
                            table_name = table_config.get("table_name")
                            if table_name:
                                from sqlalchemy import text, inspect
                                inspector = inspect(db.bind)
                                if table_name in inspector.get_table_names():
                                    result = db.execute(text(f"SELECT COUNT(*) as cnt FROM `{table_name}`"))
                                    row = result.fetchone()
                                    count_before = row[0] if row else 0
                                    print(f"     └─ 导入前记录数: {count_before} (表: {table_name})")
                except Exception:
                    pass
            sheet_name = raw_sheet.sheet_name
            worksheet = workbook[sheet_name]
            
            try:
                # 5.1 Dispatcher分派parser（如果上面已经dispatch过，这里可以重用结果）
                # 为了代码清晰，这里重新dispatch（实际可以优化）
                dispatch_result = dispatcher.dispatch_sheet(
                    sheet_name=sheet_name,
                    worksheet=worksheet
                )
                
                action = dispatch_result.get("action")
                parser_type = dispatch_result.get("parser")
                sheet_config = dispatch_result.get("sheet_config")
                
                # 如果上面已经获取了table_name和count_before，这里重用
                if sheet_config and not table_name:
                    table_config = sheet_config.get("table_config")
                    if table_config:
                        from app.services.sheet_table_mapper import get_table_name_for_sheet
                        table_name = table_config.get("table_name") or get_table_name_for_sheet(
                            sheet_name=sheet_name,
                            source_code=profile.source_code,
                            dataset_type=profile.dataset_type
                        )
                
                # 5.2 根据action处理
                if action == "SKIP_META":
                    print(f"     └─ ⏭️  跳过（元数据sheet）", flush=True)
                    update_sheet_parse_status(
                        db=db,
                        raw_sheet_id=raw_sheet.id,
                        parse_status="skipped",
                        parser_type=None
                    )
                    continue
                
                elif action == "RAW_TABLE_STORE_ONLY":
                    print(f"     └─ 📦 仅存储到raw_table（不解析）", flush=True)
                    update_sheet_parse_status(
                        db=db,
                        raw_sheet_id=raw_sheet.id,
                        parse_status="raw_only",
                        parser_type=None
                    )
                    continue
                
                elif action == "PARSE" and parser_type and sheet_config:
                    # 5.3 调用parser解析
                    table_config = sheet_config.get("table_config")
                    
                    print(f"     └─ 使用解析器: {parser_type}", flush=True)
                    if table_config:
                        print(f"     └─ 目标表: {table_config.get('table_name', '未知')}", flush=True)
                    
                    try:
                        parser = get_parser(parser_type)
                    except ValueError as e:
                        error_msg = str(e)
                        if "未知的解析器类型" in error_msg:
                            print(f"     └─ ❌ Sheet处理失败: {error_msg}", flush=True)
                            error_collector.add_error(
                                sheet_name=sheet_name,
                                row_no=None,
                                column=None,
                                error_type="PARSER_NOT_FOUND",
                                error_message=f"不支持的解析器类型: {parser_type}",
                                raw_value=None,
                                context=f"sheet_name={sheet_name}, parser_type={parser_type}"
                            )
                            # 更新sheet状态
                            update_sheet_parse_status(
                                db=db,
                                raw_sheet_id=raw_sheet.id,
                                parse_status="failed",
                                parser_type=parser_type,
                                error_count=1
                            )
                            continue
                        else:
                            raise
                    
                    print(f"     └─ 开始解析数据...", flush=True)
                    
                    # 调试：检查sheet_config是否包含metric_template
                    if sheet_config:
                        metric_template = sheet_config.get("metric_template")
                        if not metric_template:
                            print(f"     └─ ⚠️  sheet_config中没有metric_template！", flush=True)
                            print(f"         sheet_config.keys()={list(sheet_config.keys())[:15]}", flush=True)
                        else:
                            metric_key = metric_template.get("metric_key", "")
                            print(f"     └─ ✓ metric_template存在: metric_key={metric_key}", flush=True)
                    
                    observations = parser.parse(
                        sheet_data=worksheet,
                        sheet_config=sheet_config,
                        profile_defaults=profile.defaults_json or {},
                        source_code=profile.source_code,
                        batch_id=batch.id
                    )
                    
                    print(f"     └─ 解析得到观测值: {len(observations)} 条", flush=True)
                    
                    # 5.4 验证数据
                    validator = ObservationValidator(error_collector)
                    # 对于新架构（有table_config），跳过metric_key和dedup_key检查
                    skip_metric_check = bool(table_config)
                    
                    # 调试：检查前几条数据的结构
                    if observations and len(observations) > 0:
                        sample_obs = observations[0]
                        print(f"     └─ 示例观测值结构: obs_date={sample_obs.get('obs_date')}, value={sample_obs.get('value')}, period_type={sample_obs.get('period_type')}")
                    
                    valid_observations = validator.validate_batch(
                        observations, 
                        sheet_name,
                        skip_metric_key_check=skip_metric_check
                    )
                    
                    print(f"     └─ 验证后有效观测值: {len(valid_observations)} 条", flush=True)
                    if len(valid_observations) == 0 and len(observations) > 0:
                        # 调试：查看第一个失败的原因
                        is_valid, error_msg = validator.validate_observation(
                            observations[0],
                            sheet_name,
                            row_no=1,
                            skip_metric_key_check=skip_metric_check
                        )
                        print(f"     └─ ⚠️  第一个观测值验证失败: {error_msg}", flush=True)
                    
                    # 5.5 检查是否有table_config（新架构：导入到独立表）
                    
                    if table_config and valid_observations:
                        # 使用新架构：导入到独立表
                        try:
                            print(f"     └─ ✅ 使用新架构（独立表）", flush=True)
                            from app.services.sheet_table_mapper import get_table_name_for_sheet
                            from app.services.column_mapper import ColumnMapper
                            from app.services.sheet_table_importer import SheetTableImporter
                            
                            # table_name在sheet_config顶层，不在table_config里面
                            table_name = sheet_config.get("table_name") or get_table_name_for_sheet(
                                sheet_name=sheet_name,
                                source_code=profile.source_code,
                                dataset_type=profile.dataset_type
                            )
                            
                            column_mapping = table_config.get("column_mapping", {})
                            unique_key = table_config.get("unique_key", [])
                            
                            # 转换数据
                            print(f"     └─ 开始转换数据...", flush=True)
                            mapper = ColumnMapper()
                            records = mapper.map_observations_to_table_records(
                                observations=valid_observations,
                                column_mapping=column_mapping,
                                table_name=table_name,
                                batch_id=batch_id,
                                sheet_config=sheet_config
                            )
                            
                            # 导入到表
                            print(f"     └─ 转换后记录数: {len(records)} 条", flush=True)
                            print(f"     └─ 开始导入到表 {table_name}...", flush=True)
                            
                            importer = SheetTableImporter(db)
                            import_result = importer.import_to_table(
                                table_name=table_name,
                                records=records,
                                unique_key=unique_key
                            )
                            
                            # ========== Sheet导入后日志 ==========
                            count_after = -1
                            try:
                                from sqlalchemy import inspect, text
                                inspector = inspect(db.bind)
                                if table_name in inspector.get_table_names():
                                    result_count = db.execute(text(f"SELECT COUNT(*) as cnt FROM `{table_name}`"))
                                    row = result_count.fetchone()
                                    count_after = row[0] if row else 0
                            except Exception:
                                count_after = -1
                            
                            inserted = import_result.get("inserted", 0)
                            updated = import_result.get("updated", 0)
                            errors = import_result.get("errors", 0)
                            
                            print(f"     └─ ✅ Sheet导入完成", flush=True)
                            if count_after >= 0:
                                print(f"     └─ 导入后记录数: {count_after}", flush=True)
                                if count_before is not None and count_before >= 0:
                                    print(f"     └─ 新增记录数: {count_after - count_before}", flush=True)
                            print(f"     └─ 插入: {inserted}, 更新: {updated}, 错误: {errors}", flush=True)
                            print(f"     └─ 完成时间: {datetime.now().strftime('%H:%M:%S')}", flush=True)
                            
                            inserted_count += inserted
                            updated_count += updated
                            error_count += errors
                            
                            # ========== 新架构：同时导入到fact_observation ==========
                            # 对于有table_config的sheet，也需要导入到fact_observation供前端查询
                            try:
                                print(f"     └─ 同时导入到fact_observation...", flush=True)
                                upsert_result = upsert_observations(
                                    db=db,
                                    observations=valid_observations,
                                    batch_id=batch_id,
                                    sheet_name=sheet_name
                                )
                                obs_inserted = upsert_result.get("inserted", 0)
                                obs_updated = upsert_result.get("updated", 0)
                                obs_errors = upsert_result.get("errors", 0)
                                print(f"     └─ fact_observation: 插入: {obs_inserted}, 更新: {obs_updated}, 错误: {obs_errors}", flush=True)
                            except Exception as e:
                                error_msg = str(e)
                                if len(error_msg) > 200:
                                    error_msg = error_msg[:197] + "..."
                                print(f"     └─ ⚠️  导入到fact_observation失败: {error_msg}", flush=True)
                                # 不影响主流程，只记录错误
                            
                        except Exception as e:
                            error_msg = str(e)
                            if len(error_msg) > 200:
                                error_msg = error_msg[:197] + "..."
                            error_collector.record_error(
                                error_type="sheet_table_import_error",
                                message=f"导入到独立表失败: {error_msg}",
                                sheet_name=sheet_name,
                                immediate=True
                            )
                            error_count += len(valid_observations)
                            print(f"     └─ ❌ Sheet导入失败: {error_msg}", flush=True)
                            import traceback
                            traceback.print_exc()
                    elif valid_observations:
                        # 兼容旧架构：导入到fact_observation
                        print(f"     ℹ️  使用旧架构导入到fact_observation", flush=True)
                        
                        upsert_result = upsert_observations(
                            db=db,
                            observations=valid_observations,
                            batch_id=batch_id,
                            sheet_name=sheet_name
                        )
                        
                        inserted = upsert_result.get("inserted", 0)
                        updated = upsert_result.get("updated", 0)
                        errors = upsert_result.get("errors", 0)
                        
                        print(f"     ✅ Sheet导入完成: {sheet_name}")
                        print(f"        插入: {inserted}, 更新: {updated}, 错误: {errors}")
                        
                        inserted_count += inserted
                        updated_count += updated
                        error_count += errors
                    
                    observation_count = len(valid_observations)
                    
                    update_sheet_parse_status(
                        db=db,
                        raw_sheet_id=raw_sheet.id,
                        parse_status="parsed",
                        parser_type=parser_type,
                        observation_count=observation_count,
                        error_count=len(observations) - len(valid_observations)
                    )
                    
                    # 记录sheet处理完成
                    if table_config:
                        table_name = table_config.get("table_name")
                        if table_name:
                            try:
                                from sqlalchemy import text, inspect
                                inspector = inspect(db.bind)
                                if table_name in inspector.get_table_names():
                                    result = db.execute(text(f"SELECT COUNT(*) as cnt FROM `{table_name}`"))
                                    row = result.fetchone()
                                    count_after = row[0] if row else 0
                                    inserted = count_after - count_before if count_before is not None else 0
                                    print(f"     └─ 导入后记录数: {count_after} (新增: {inserted})")
                                    print(f"     └─ 完成时间: {datetime.now().strftime('%H:%M:%S')}")
                            except Exception:
                                pass
                    
                    parsed_sheets += 1
                    
                    if not valid_observations:
                        print(f"     ⚠️  Sheet无有效数据: {sheet_name}", flush=True)
                
                else:
                    # 无法解析（但RAW_TABLE_STORE_ONLY不应该到这里）
                    # 如果action是RAW_TABLE_STORE_ONLY但没被处理，说明逻辑有问题
                    if action == "RAW_TABLE_STORE_ONLY":
                        # 这种情况不应该发生，但为了安全起见，还是标记为raw_only
                        print(f"     └─ ⚠️  未处理的RAW_TABLE_STORE_ONLY，标记为raw_only")
                        update_sheet_parse_status(
                            db=db,
                            raw_sheet_id=raw_sheet.id,
                            parse_status="raw_only",
                            parser_type=None
                        )
                        continue
                    
                    # 真正的无法解析
                    print(f"     └─ ❌ 无法解析: action={action}, parser={parser_type}")
                    error_collector.record_error(
                        error_type="parse_failed",
                        message=f"无法分派parser: action={action}, parser={parser_type}",
                        sheet_name=sheet_name,
                        immediate=True
                    )
                    update_sheet_parse_status(
                        db=db,
                        raw_sheet_id=raw_sheet.id,
                        parse_status="failed",
                        parser_type=None
                    )
            
            except Exception as e:
                # Sheet处理失败
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:197] + "..."
                print(f"     └─ ❌ Sheet处理失败: {error_msg}", flush=True)
                import traceback
                traceback.print_exc()
                error_collector.record_error(
                    error_type="sheet_error",
                    message=f"Sheet处理失败: {error_msg}",
                    sheet_name=sheet_name,
                    immediate=True
                )
                update_sheet_parse_status(
                    db=db,
                    raw_sheet_id=raw_sheet.id,
                    parse_status="failed",
                    parser_type=None
                )
                continue
            
            # 每个sheet处理完后提交
            db.commit()
        
        # 6. 刷新错误收集器
        error_collector.flush()
        
        # 7. 触发指标抽取
        try:
            from app.services.indicator_extractor import extract_core_indicators
            extract_result = extract_core_indicators(db=db, batch_id=batch_id)
            # 记录抽取结果（可选）
        except Exception as e:
            # 抽取失败不影响导入结果
            pass
        
        # 8. 更新batch状态
        error_count = error_collector.get_error_count()
        if batch:
            batch.status = "success" if error_count == 0 else "partial"
            batch.inserted_count = inserted_count
            batch.updated_count = updated_count
            batch.success_rows = inserted_count + updated_count
            batch.failed_rows = error_count
            batch.sheet_count = total_sheets
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            batch.duration_ms = duration_ms
        
        db.commit()
        
        return {
            "success": True,
            "batch_id": batch_id,
            "inserted": inserted_count,
            "updated": updated_count,
            "total_sheets": total_sheets,
            "parsed_sheets": parsed_sheets,
            "errors": error_count
        }
    
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        if len(error_msg) > 500:
            error_msg = error_msg[:497] + "..."
        return {
            "success": False,
            "batch_id": batch_id if 'batch_id' in locals() else None,
            "inserted": inserted_count,
            "updated": updated_count,
            "errors": [{"reason": f"导入失败: {error_msg}"}]
        }
