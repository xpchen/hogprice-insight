"""涌益周度导入器（多行表头/合并单元格）"""
import pandas as pd
from io import BytesIO
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import FactIndicatorTs, DimIndicator, DimRegion
from app.services.region_mapping_service import get_or_create_region, resolve_region_code
from app.utils.value_cleaner import clean_numeric_value
from app.utils.region_normalizer import normalize_province_name
from app.utils.wide_table_parser import parse_multirow_header_wide_table
from app.services.indicator_mapping_service import resolve_indicator_code, get_indicator_config


def import_yongyi_weekly(db: Session, file_content: bytes, batch_id: int) -> Dict:
    """
    导入涌益周度数据
    
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
    
    try:
        excel_file = pd.ExcelFile(BytesIO(file_content), engine='openpyxl')
        sheet_names = excel_file.sheet_names
        
        for sheet_name in sheet_names:
            try:
                # 跳过非数据sheet
                if sheet_name.startswith('Sheet') and '周度' not in sheet_name:
                    continue
                
                result = _import_weekly_sheet(db, excel_file, sheet_name, batch_id)
                
                inserted_count += result.get("inserted", 0)
                updated_count += result.get("updated", 0)
                errors.extend(result.get("errors", []))
                
            except Exception as e:
                # 截断过长的错误消息
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:197] + "..."
                errors.append({
                    "sheet": sheet_name,
                    "reason": f"处理失败: {error_msg}"
                })
                continue
        
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


def _import_weekly_sheet(db: Session, excel_file, sheet_name: str, batch_id: int) -> Dict:
    """导入单个周度sheet"""
    errors = []
    inserted_count = 0
    updated_count = 0
    
    try:
        # 使用多行表头解析工具
        df_long = parse_multirow_header_wide_table(
            excel_file,
            sheet_name,
            header_start_row=None,  # 自动识别
            region_col=0
        )
        
        if df_long.empty:
            return {
                "inserted": 0,
                "updated": 0,
                "errors": [{"sheet": sheet_name, "reason": "解析结果为空"}]
            }
        
        # 按field分组处理（每个field可能对应不同的指标）
        for field_name, group_df in df_long.groupby('field'):
            # 解析指标代码
            indicator_code = resolve_indicator_code(sheet_name, str(field_name) if field_name else "*")
            
            if not indicator_code:
                # 如果无法解析，尝试从sheet名称推断
                if "体重" in sheet_name or "均重" in str(field_name):
                    indicator_code = "hog_weight_out_week"
                elif "利润" in sheet_name or "利润" in str(field_name):
                    indicator_code = "profit_breeding"
                elif "价格" in sheet_name or "价格" in str(field_name):
                    indicator_code = "hog_price_out_week"
                elif "冻品" in sheet_name or "库存" in str(field_name):
                    indicator_code = "frozen_capacity_rate"
                elif "饲料" in sheet_name or "全价料" in str(field_name):
                    indicator_code = "feed_price_full"
                else:
                    errors.append({
                        "sheet": sheet_name,
                        "field": field_name,
                        "reason": f"无法解析指标代码"
                    })
                    continue
            
            # 获取指标配置
            config = get_indicator_config(indicator_code)
            if not config:
                # 创建默认配置
                config = {
                    "indicator_code": indicator_code,
                    "indicator_name": indicator_code,
                    "freq": "W",
                    "unit": None,
                    "topic": "产业链"
                }
            
            # 获取或创建指标维度
            indicator = db.query(DimIndicator).filter(
                DimIndicator.indicator_code == indicator_code
            ).first()
            
            if not indicator:
                indicator = DimIndicator(
                    indicator_code=indicator_code,
                    indicator_name=config.get("indicator_name", indicator_code),
                    freq="W",
                    unit=config.get("unit"),
                    topic=config.get("topic"),
                    source_code="YONGYI",
                    calc_method="RAW"
                )
                db.add(indicator)
                db.flush()
            
            # 处理每一行
            records_to_insert = []
            
            for idx, row in group_df.iterrows():
                try:
                    week_start = row['week_start']
                    week_end = row['week_end']
                    region_name = str(row['region']).strip()
                    value = clean_numeric_value(row['value'])
                    
                    if value is None:
                        continue
                    
                    # 使用统一的区域映射服务（严格验证）
                    region = get_or_create_region(db, region_name=region_name, strict=True)
                    if not region:
                        # 跳过无效的区域名称
                        continue
                    region_code = region.region_code
                    
                    # 检查是否已存在
                    existing = db.query(FactIndicatorTs).filter(
                        FactIndicatorTs.indicator_code == indicator_code,
                        FactIndicatorTs.region_code == region_code,
                        FactIndicatorTs.freq == "W",
                        FactIndicatorTs.week_end == week_end
                    ).first()
                    
                    if existing:
                        existing.value = value
                        existing.week_start = week_start
                        existing.ingest_batch_id = batch_id
                        updated_count += 1
                    else:
                        records_to_insert.append(FactIndicatorTs(
                            indicator_code=indicator_code,
                            region_code=region_code,
                            freq="W",
                            week_start=week_start,
                            week_end=week_end,
                            value=value,
                            source_code="YONGYI",
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
                        "field": field_name,
                        "reason": f"处理失败: {error_msg}"
                    })
                    continue
            
            # 批量插入
            if records_to_insert:
                db.bulk_save_objects(records_to_insert)
                db.flush()
        
        return {
            "inserted": inserted_count,
            "updated": updated_count,
            "errors": errors
        }
        
    except Exception as e:
        # 截断过长的错误消息
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:197] + "..."
        return {
            "inserted": 0,
            "updated": 0,
            "errors": [{"sheet": sheet_name, "reason": f"周度处理失败: {error_msg}"}]
        }
