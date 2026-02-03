"""涌益日度导入器（独立版本，专门处理涌益日度数据）"""
import pandas as pd
import re
from io import BytesIO
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, date

from app.models import FactIndicatorTs, DimIndicator, DimRegion
from app.utils.value_cleaner import clean_numeric_value
from app.utils.region_normalizer import normalize_province_name
from app.utils.wide_table_parser import parse_wide_table_with_dates
from app.services.indicator_mapping_service import resolve_indicator_code


def import_yongyi_daily_v2(db: Session, file_content: bytes, batch_id: int) -> Dict:
    """
    导入涌益日度数据（独立版本，专门处理涌益日度数据格式）
    
    Args:
        db: 数据库会话
        file_content: Excel文件内容（bytes）
        batch_id: 导入批次ID
    
    Returns:
        {
            "success": bool,
            "inserted": int,
            "updated": int,
            "errors": List[Dict]
        }
    """
    errors = []
    inserted_count = 0
    updated_count = 0
    
    # 验证 batch_id 是否存在
    from app.models import ImportBatch
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        return {
            "success": False,
            "inserted": 0,
            "updated": 0,
            "errors": [{"reason": f"批次ID {batch_id} 不存在"}]
        }
    
    # 保存原始文件内容，供宽表解析使用
    original_file_content = file_content
    
    try:
        excel_file = pd.ExcelFile(BytesIO(file_content), engine='openpyxl')
        sheet_names = excel_file.sheet_names
        
        total_sheets = len(sheet_names)
        for sheet_idx, sheet_name in enumerate(sheet_names):
            try:
                # 判断是窄表还是宽表
                is_wide_table = _is_wide_table_structure(excel_file, sheet_name)
                
                if is_wide_table:
                    # 宽表处理（日期跨列）
                    result = _import_wide_table(db, excel_file, sheet_name, batch_id, source_code="YONGYI", file_content=original_file_content)
                else:
                    # 窄表处理（标准格式：日期列 + 指标列）
                    result = _import_narrow_table(db, excel_file, sheet_name, batch_id, source_code="YONGYI")
                
                inserted_count += result.get("inserted", 0)
                updated_count += result.get("updated", 0)
                errors.extend(result.get("errors", []))
                
                # 每个sheet处理完后立即提交，避免事务过长导致锁超时
                try:
                    db.commit()
                except Exception as commit_error:
                    db.rollback()
                    error_msg = str(commit_error)
                    if len(error_msg) > 200:
                        error_msg = error_msg[:197] + "..."
                    errors.append({
                        "sheet": sheet_name,
                        "reason": f"提交失败: {error_msg}"
                    })
                    # 继续处理下一个sheet
                    continue
                
            except Exception as e:
                # 如果处理失败，回滚当前sheet的事务
                try:
                    db.rollback()
                except:
                    pass
                
                # 截断过长的错误消息
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:197] + "..."
                errors.append({
                    "sheet": sheet_name,
                    "reason": f"处理失败: {error_msg}"
                })
                # 继续处理下一个sheet
                continue
        
        # 最终提交
        db.commit()
        
        return {
            "success": True,
            "inserted": inserted_count,
            "updated": updated_count,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        # 截断过长的错误消息
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:197] + "..."
        return {
            "success": False,
            "inserted": inserted_count,
            "updated": updated_count,
            "errors": errors + [{"reason": f"导入失败: {error_msg}"}]
        }


def _is_wide_table_structure(excel_file, sheet_name: str) -> bool:
    """判断是否是宽表结构（日期跨列）"""
    try:
        df_sample = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=10, engine='openpyxl')
        # 宽表特征：第一列不是日期，而是区域或其他维度
        # 或者有多行表头
        if df_sample.empty:
            return False
        
        # 检查第一列是否是日期格式
        first_col = df_sample.iloc[:, 0]
        date_count = 0
        for val in first_col.head(10):
            try:
                pd.to_datetime(val)
                date_count += 1
            except:
                pass
        
        # 如果第一列大部分不是日期，可能是宽表
        return date_count < len(first_col.head(10)) * 0.5
    except:
        return False


def _import_narrow_table(db: Session, excel_file, sheet_name: str, batch_id: int, source_code: str = "YONGYI") -> Dict:
    """导入窄表格式（标准格式：日期列 + 指标列）"""
    errors = []
    inserted_count = 0
    updated_count = 0
    
    try:
        # 读取数据
        df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
        
        if df.empty:
            return {
                "inserted": 0,
                "updated": 0,
                "errors": [{"sheet": sheet_name, "reason": "数据为空"}]
            }
        
        # 第一列应该是日期
        date_col = df.iloc[:, 0]
        
        # 处理每一列（从第二列开始，对应指标）
        for col_idx in range(1, df.shape[1]):
            col_name = str(df.columns[col_idx]).strip()
            
            # 跳过空列名
            if not col_name or col_name.lower() in ['nan', 'none', '']:
                continue
            
            # 解析指标代码
            indicator_code = resolve_indicator_code(sheet_name, col_name)
            
            if not indicator_code:
                errors.append({
                    "sheet": sheet_name,
                    "col": col_name,
                    "reason": f"无法解析指标代码"
                })
                continue
            
            # 获取或创建指标维度
            indicator = db.query(DimIndicator).filter(
                DimIndicator.indicator_code == indicator_code
            ).first()
            
            if not indicator:
                indicator = DimIndicator(
                    indicator_code=indicator_code,
                    indicator_name=col_name,
                    freq="D",
                    unit=None,
                    topic="价格",
                    source_code=source_code,
                    calc_method="RAW"
                )
                db.add(indicator)
                db.flush()
            
            # 默认区域为全国
            region_code = "NATION"
            
            # 处理数据行
            records_to_insert = []
            value_col = df.iloc[:, col_idx]
            
            for row_idx, (date_val, value_val) in enumerate(zip(date_col, value_col)):
                try:
                    # 跳过空日期
                    if pd.isna(date_val):
                        continue
                    
                    # 解析日期
                    trade_date_parsed = pd.to_datetime(date_val, errors='coerce')
                    if pd.isna(trade_date_parsed):
                        continue
                    
                    trade_date = trade_date_parsed.date()
                    
                    # 检查日期是否合理（不能是1970年，这通常是解析失败的默认值）
                    if trade_date.year < 2000 or trade_date.year > 2100:
                        errors.append({
                            "sheet": sheet_name,
                            "row": row_idx + 2,
                            "col": col_name,
                            "reason": f"日期不合理: {trade_date} (原始值: {date_val})"
                        })
                        continue
                    
                    # 清洗数值
                    value = clean_numeric_value(value_val)
                    if value is None:
                        continue
                    
                    # 检查是否已存在
                    existing = db.query(FactIndicatorTs).filter(
                        FactIndicatorTs.indicator_code == indicator_code,
                        FactIndicatorTs.region_code == region_code,
                        FactIndicatorTs.freq == "D",
                        FactIndicatorTs.trade_date == trade_date
                    ).first()
                    
                    if existing:
                        existing.value = value
                        existing.ingest_batch_id = batch_id
                        updated_count += 1
                    else:
                        records_to_insert.append(FactIndicatorTs(
                            indicator_code=indicator_code,
                            region_code=region_code,
                            freq="D",
                            trade_date=trade_date,
                            value=value,
                            source_code=source_code,
                            ingest_batch_id=batch_id
                        ))
                        inserted_count += 1
                        
                except Exception as e:
                    # 截断过长的错误消息
                    error_msg = str(e)
                    if len(error_msg) > 200:
                        error_msg = error_msg[:197] + "..."
                    errors.append({
                        "sheet": sheet_name,
                        "row": row_idx + 2,
                        "col": col_name,
                        "reason": f"处理失败: {error_msg}"
                    })
                    continue
            
            # 分批插入，避免一次性插入太多数据导致锁超时
            if records_to_insert:
                batch_size = 1000  # 每批插入1000条
                for i in range(0, len(records_to_insert), batch_size):
                    batch_records = records_to_insert[i:i + batch_size]
                    db.bulk_save_objects(batch_records)
                    db.flush()  # 每批flush一次，避免内存占用过大
        
        return {
            "inserted": inserted_count,
            "updated": updated_count,
            "errors": errors
        }
        
    except Exception as e:
        # 回滚当前sheet的事务
        try:
            db.rollback()
        except:
            pass
        
        # 截断过长的错误消息
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:197] + "..."
        return {
            "inserted": 0,
            "updated": 0,
            "errors": [{"sheet": sheet_name, "reason": f"窄表处理失败: {error_msg}"}]
        }


def _import_wide_table(db: Session, excel_file, sheet_name: str, batch_id: int, source_code: str = "YONGYI", file_content: bytes = None) -> Dict:
    """导入宽表格式（日期跨列）"""
    errors = []
    inserted_count = 0
    updated_count = 0
    
    try:
        # 使用宽表解析器
        # excel_file 是 pd.ExcelFile 对象，需要转换为 openpyxl workbook
        from openpyxl import load_workbook
        
        # 获取原始文件内容
        if file_content is None:
            # 从 pd.ExcelFile 的底层文件对象获取
            if hasattr(excel_file, 'io'):
                file_content = excel_file.io.read()
                excel_file.io.seek(0)  # 重置文件指针
            else:
                # 如果是 BytesIO，直接使用
                file_content = excel_file.read()
                excel_file.seek(0)
        
        # 加载为 openpyxl workbook
        wb = load_workbook(BytesIO(file_content), data_only=True)
        df_long = parse_wide_table_with_dates(wb, sheet_name)
        
        if df_long.empty:
            return {
                "inserted": 0,
                "updated": 0,
                "errors": [{"sheet": sheet_name, "reason": "数据为空"}]
            }
        
        # 获取指标代码（从sheet名称或第一行推断）
        indicator_code = resolve_indicator_code(sheet_name, "*")
        
        if not indicator_code:
            errors.append({
                "sheet": sheet_name,
                "reason": f"无法解析指标代码"
            })
            return {
                "inserted": 0,
                "updated": 0,
                "errors": errors
            }
        
        # 获取或创建指标维度
        indicator = db.query(DimIndicator).filter(
            DimIndicator.indicator_code == indicator_code
        ).first()
        
        if not indicator:
            indicator = DimIndicator(
                indicator_code=indicator_code,
                indicator_name=sheet_name,
                freq="D",
                unit=None,
                topic="价格",
                source_code=source_code,
                calc_method="RAW"
            )
            db.add(indicator)
            db.flush()
        
        # 处理每一行
        records_to_insert = []
        
        for idx, row in df_long.iterrows():
            try:
                region_name = str(row['region']).strip()
                trade_date = row['trade_date']
                value = clean_numeric_value(row['value'])
                
                if value is None:
                    continue
                
                # 使用统一的区域映射服务
                region = get_or_create_region(db, region_name=region_name)
                region_code = region.region_code
                
                # 检查是否已存在
                existing = db.query(FactIndicatorTs).filter(
                    FactIndicatorTs.indicator_code == indicator_code,
                    FactIndicatorTs.region_code == region_code,
                    FactIndicatorTs.freq == "D",
                    FactIndicatorTs.trade_date == trade_date
                ).first()
                
                if existing:
                    existing.value = value
                    existing.ingest_batch_id = batch_id
                    updated_count += 1
                else:
                    records_to_insert.append(FactIndicatorTs(
                        indicator_code=indicator_code,
                        region_code=region_code,
                        freq="D",
                        trade_date=trade_date,
                        value=value,
                        source_code=source_code,
                        ingest_batch_id=batch_id
                    ))
                    inserted_count += 1
                    
            except Exception as e:
                # 截断过长的错误消息
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:197] + "..."
                errors.append({
                    "sheet": sheet_name,
                    "row": idx + 1,
                    "reason": f"处理失败: {error_msg}"
                })
                continue
        
        # 分批插入，避免一次性插入太多数据导致锁超时
        if records_to_insert:
            batch_size = 1000  # 每批插入1000条
            for i in range(0, len(records_to_insert), batch_size):
                batch_records = records_to_insert[i:i + batch_size]
                db.bulk_save_objects(batch_records)
                db.flush()  # 每批flush一次，避免内存占用过大
        
        return {
            "inserted": inserted_count,
            "updated": updated_count,
            "errors": errors
        }
        
    except Exception as e:
        # 回滚当前sheet的事务
        try:
            db.rollback()
        except:
            pass
        
        # 截断过长的错误消息
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:197] + "..."
        return {
            "inserted": 0,
            "updated": 0,
            "errors": [{"sheet": sheet_name, "reason": f"宽表处理失败: {error_msg}"}]
        }
