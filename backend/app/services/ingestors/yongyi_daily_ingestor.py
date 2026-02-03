"""涌益日度导入器（支持窄表和宽表）"""
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
from app.services.region_mapping_service import get_or_create_region, resolve_region_code


def import_yongyi_daily(db: Session, file_content: bytes, batch_id: int, source_code: str = "YONGYI") -> Dict:
    """
    导入涌益日度数据
    
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
        
        total_sheets = len(sheet_names)
        for sheet_idx, sheet_name in enumerate(sheet_names):
            try:
                # 检查是否是旧格式（钢联数据格式）
                is_legacy_format = _is_legacy_format(excel_file, sheet_name)
                
                if is_legacy_format:
                    # 旧格式处理（钢联数据格式）
                    result = _import_legacy_format(db, excel_file, sheet_name, batch_id, source_code)
                else:
                    # 判断是窄表还是宽表
                    is_wide_table = _is_wide_table_structure(excel_file, sheet_name)
                    
                    if is_wide_table:
                        # 宽表处理（日期跨列）
                        result = _import_wide_table(db, excel_file, sheet_name, batch_id, source_code)
                    else:
                        # 窄表处理（标准格式：日期列 + 指标列）
                        result = _import_narrow_table(db, excel_file, sheet_name, batch_id, source_code)
                
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


def _is_legacy_format(excel_file, sheet_name: str) -> bool:
    """判断是否为旧格式（钢联数据格式）"""
    try:
        # 读取前5行判断结构
        df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=5, header=None, engine='openpyxl')
        
        # 旧格式特征：第1行第1列是"钢联数据"，第2行是指标名称，第3行是单位，第4行是更新时间
        if df.shape[0] >= 4:
            first_cell = str(df.iloc[0, 0]).strip() if pd.notna(df.iloc[0, 0]) else ""
            if first_cell == '钢联数据':
                return True
        
        return False
    except:
        return False


def _is_wide_table_structure(excel_file, sheet_name: str) -> bool:
    """判断是否为宽表结构（日期跨列）"""
    try:
        # 读取前几行判断结构
        df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=5, header=None, engine='openpyxl')
        
        # 宽表特征：第一列是省份/区域，后续列是日期
        if df.shape[1] > 10:  # 列数较多，可能是宽表
            # 检查第一列是否包含省份名称
            first_col = df.iloc[:, 0].astype(str).str.strip()
            province_keywords = ['北京', '上海', '广东', '山东', '河南', '四川', '江苏', '湖北']
            if any(keyword in ' '.join(first_col.values) for keyword in province_keywords):
                return True
        
        return False
    except:
        return False


def _import_narrow_table(db: Session, excel_file, sheet_name: str, batch_id: int, source_code: str = "YONGYI") -> Dict:
    """导入窄表（标准格式）"""
    errors = []
    inserted_count = 0
    updated_count = 0
    
    try:
        # 读取数据（假设第一列是日期，后续列是指标）
        df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
        
        # 识别日期列（通常是第一列）
        date_col = df.iloc[:, 0]
        
        # 处理每一列（从第二列开始）
        for col_idx in range(1, df.shape[1]):
            col_name = df.columns[col_idx] if hasattr(df.columns, '__getitem__') else f"Column_{col_idx}"
            
            # 解析指标代码
            indicator_code = resolve_indicator_code(sheet_name, str(col_name))
            if not indicator_code:
                # 如果无法解析，跳过
                continue
            
            # 获取或创建指标维度
            indicator = db.query(DimIndicator).filter(
                DimIndicator.indicator_code == indicator_code
            ).first()
            
            if not indicator:
                # 创建新指标（需要从映射配置获取完整信息）
                from app.services.indicator_mapping_service import get_indicator_config
                config = get_indicator_config(indicator_code)
                if config:
                    indicator = DimIndicator(
                        indicator_code=indicator_code,
                        indicator_name=config.get("indicator_name", indicator_code),
                        freq=config.get("freq", "D"),
                        unit=config.get("unit"),
                        topic=config.get("topic"),
                        source_code=source_code,
                        calc_method="RAW"
                    )
                    db.add(indicator)
                    db.flush()
            
            # 处理数据行
            value_col = df.iloc[:, col_idx]
            records_to_insert = []
            
            for row_idx, (date_val, value_val) in enumerate(zip(date_col, value_col)):
                try:
                    # 解析日期
                    if pd.isna(date_val):
                        continue
                    
                    # 使用 errors='coerce' 确保解析失败时返回 NaT
                    trade_date_parsed = pd.to_datetime(date_val, errors='coerce')
                    if pd.isna(trade_date_parsed):
                        errors.append({
                            "sheet": sheet_name,
                            "row": row_idx + 2,
                            "col": col_name,
                            "reason": f"日期解析失败: {date_val}"
                        })
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
                    
                    # 默认区域为全国
                    region_code = "NATION"
                    
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


def _import_legacy_format(db: Session, excel_file, sheet_name: str, batch_id: int, source_code: str = "GANGLIAN") -> Dict:
    """导入旧格式（钢联数据格式）
    
    格式说明：
    - 第1行：标题（"钢联数据"）
    - 第2行：指标名称行（包含完整的指标名称，如"商品猪：出栏均价：中国（日）"）
    - 第3行：单位行
    - 第4行：更新时间行
    - 第5行开始：数据行（日期在第一列，数据在后续列）
    """
    errors = []
    inserted_count = 0
    updated_count = 0
    
    try:
        # 读取数据（跳过前4行，从第5行开始）
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, engine='openpyxl', skiprows=4)
        
        # 读取指标名称行（第2行，索引为1）
        indicator_names_df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, engine='openpyxl', nrows=1, skiprows=1)
        indicator_names = indicator_names_df.iloc[0].tolist()
        
        # 读取单位行（第3行，索引为2）
        units_df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, engine='openpyxl', nrows=1, skiprows=2)
        units = units_df.iloc[0].tolist()
        
        if df.empty:
            return {
                "inserted": 0,
                "updated": 0,
                "errors": [{"sheet": sheet_name, "reason": "数据为空"}]
            }
        
        # 第一列是日期
        date_col = df.iloc[:, 0]
        
        # 处理每一列（从第二列开始，对应指标）
        for col_idx in range(1, min(df.shape[1], len(indicator_names))):
            indicator_name = str(indicator_names[col_idx]).strip() if col_idx < len(indicator_names) else f"Column_{col_idx}"
            unit = str(units[col_idx]).strip() if col_idx < len(units) else None
            
            # 跳过空指标名称
            if not indicator_name or indicator_name.lower() in ['nan', 'none', '']:
                continue
            
            # 从指标名称中提取区域和指标类型
            # 格式示例："商品猪：出栏均价：中国（日）" -> 区域=中国，指标=出栏均价
            # 格式示例："商品猪：出栏均价：黑龙江（日）" -> 区域=黑龙江，指标=出栏均价
            
            # 解析区域名称
            region_name = None
            if '：' in indicator_name or ':' in indicator_name:
                parts = indicator_name.replace('：', ':').split(':')
                if len(parts) >= 3:
                    region_part = parts[2].strip()
                    # 移除括号内容，如"中国（日）" -> "中国"
                    if '（' in region_part:
                        region_name = region_part.split('（')[0].strip()
                    else:
                        region_name = region_part.strip()
            
            # 使用统一的区域映射服务
            region = get_or_create_region(db, region_name=region_name)
            region_code = region.region_code
            
            # 解析指标代码（根据指标名称和sheet名称）
            # 扩展处理：支持更多关键词和复杂指标名称
            indicator_code = None
            
            # 清理指标名称（移除特殊字符和括号内容，用于匹配）
            clean_name = indicator_name.replace('（', '(').replace('）', ')')
            # 移除括号内容，如"中国(周)" -> "中国"
            clean_name = re.sub(r'\([^)]*\)', '', clean_name)
            # 移除斜杠后的内容，如"淘汰母猪:.../标猪:..." -> "淘汰母猪:..."
            if '/' in clean_name:
                clean_name = clean_name.split('/')[0].strip()
            
            # 根据sheet名称和指标名称的关键词推断
            if "出栏均价" in indicator_name or "出栏价" in indicator_name or "市场价" in indicator_name:
                if region_code == "NATION":
                    indicator_code = "hog_price_nation"
                else:
                    indicator_code = "hog_price_province"
            elif "价差" in indicator_name:
                if "标肥" in indicator_name:
                    indicator_code = "spread_std_fat"
                elif "区域" in indicator_name:
                    indicator_code = "spread_region"
                elif "毛白" in indicator_name or "白条" in indicator_name:
                    indicator_code = "spread_hog_carcass"
                else:
                    indicator_code = "spread_std_fat"  # 默认
            elif "利润" in indicator_name or "养殖利润" in sheet_name:
                indicator_code = "profit_breeding"
            elif "二元母猪" in indicator_name:
                # 二元母猪价格
                indicator_code = "sow_price_binary"
            elif "淘汰母猪" in indicator_name:
                # 淘汰母猪价格
                indicator_code = "sow_price_cull"
            elif "白条肉" in indicator_name or "白条" in indicator_name:
                # 白条肉价格（毛白价差相关）
                indicator_code = "pork_carcass_price"
            elif "鲜猪肉" in indicator_name:
                # 鲜猪肉价格
                indicator_code = "pork_fresh_price"
            elif "冻肉" in indicator_name:
                # 冻肉价格（2号、4号等）
                indicator_code = "pork_frozen_price"
            elif "猪粮比" in indicator_name:
                # 猪粮比
                indicator_code = "hog_grain_ratio"
            elif "饲料" in indicator_name and ("比价" in indicator_name or "比" in indicator_name):
                # 饲料比价
                indicator_code = "feed_price_ratio"
            elif "标猪" in indicator_name:
                if region_code == "NATION":
                    indicator_code = "hog_price_nation"
                else:
                    indicator_code = "hog_price_province"
            else:
                # 尝试从映射配置解析
                indicator_code = resolve_indicator_code(sheet_name, indicator_name)
            
            # 如果仍然无法解析，尝试使用清理后的名称
            if not indicator_code:
                indicator_code = resolve_indicator_code(sheet_name, clean_name)
            
            # 如果还是无法解析，根据sheet名称推断
            if not indicator_code:
                if "利润" in sheet_name or "养殖" in sheet_name:
                    indicator_code = "profit_breeding"
                elif "价差" in sheet_name:
                    indicator_code = "spread_std_fat"
                elif "价格" in sheet_name:
                    if region_code == "NATION":
                        indicator_code = "hog_price_nation"
                    else:
                        indicator_code = "hog_price_province"
            
            if not indicator_code:
                errors.append({
                    "sheet": sheet_name,
                    "col": indicator_name,
                    "reason": f"无法解析指标代码"
                })
                continue
            
            # 获取或创建指标维度
            indicator = db.query(DimIndicator).filter(
                DimIndicator.indicator_code == indicator_code
            ).first()
            
            # 根据指标名称判断频率（周度数据）
            freq = "D"
            if "(周)" in indicator_name or "周度" in indicator_name or "周" in clean_name:
                freq = "W"
            
            if not indicator:
                # 根据指标代码推断topic
                topic = "价格"
                
                if "价差" in indicator_code or "spread" in indicator_code:
                    topic = "价差"
                elif "利润" in indicator_code or "profit" in indicator_code:
                    topic = "产业链"
                elif "饲料" in indicator_code or "feed" in indicator_code:
                    topic = "产业链"
                elif "比" in indicator_code or "ratio" in indicator_code:
                    topic = "产业链"
                elif "冻" in indicator_code or "frozen" in indicator_code:
                    topic = "冻品"
                elif "母猪" in indicator_code or "sow" in indicator_code:
                    topic = "价格"
                elif "猪肉" in indicator_code or "pork" in indicator_code:
                    topic = "价格"
                
                indicator = DimIndicator(
                    indicator_code=indicator_code,
                    indicator_name=indicator_name,
                    freq=freq,
                    unit=unit if unit and unit != 'nan' else None,
                    topic=topic,
                    source_code=source_code,
                    calc_method="RAW"
                )
                db.add(indicator)
                db.flush()
            
            # 处理数据行（优化：先收集所有数据，然后批量查询和插入）
            value_col = df.iloc[:, col_idx]
            
            # 第一步：收集所有有效数据
            valid_data = []
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
                    
                    # 检查日期是否合理
                    if trade_date.year < 2000 or trade_date.year > 2100:
                        continue
                    
                    # 清洗数值（处理#N/A等特殊值）
                    if pd.isna(value_val) or str(value_val).strip().upper() in ['#N/A', '#NA', 'N/A', 'NA', '']:
                        continue
                    
                    value = clean_numeric_value(value_val)
                    if value is None:
                        continue
                    
                    valid_data.append({
                        "trade_date": trade_date,
                        "value": value,
                        "row_idx": row_idx
                    })
                except Exception as e:
                    # 截断过长的错误消息
                    error_msg = str(e)
                    if len(error_msg) > 200:
                        error_msg = error_msg[:197] + "..."
                    errors.append({
                        "sheet": sheet_name,
                        "row": row_idx + 5,  # 加上跳过的4行
                        "col": indicator_name,
                        "reason": f"处理失败: {error_msg}"
                    })
                    continue
            
            if not valid_data:
                continue
            
            # 第二步：批量查询已存在的记录（优化性能）
            trade_dates = [d["trade_date"] for d in valid_data]
            
            existing_records = db.query(FactIndicatorTs).filter(
                FactIndicatorTs.indicator_code == indicator_code,
                FactIndicatorTs.region_code == region_code,
                FactIndicatorTs.freq == freq,
                FactIndicatorTs.trade_date.in_(trade_dates)
            ).all()
            
            existing_dict = {r.trade_date: r for r in existing_records}
            
            # 第三步：分类处理（更新 vs 插入）
            records_to_insert = []
            records_to_update = []
            
            for data in valid_data:
                trade_date = data["trade_date"]
                value = data["value"]
                
                if trade_date in existing_dict:
                    # 更新现有记录
                    existing = existing_dict[trade_date]
                    existing.value = value
                    existing.ingest_batch_id = batch_id
                    records_to_update.append(existing)
                    updated_count += 1
                else:
                    # 插入新记录
                    records_to_insert.append(FactIndicatorTs(
                        indicator_code=indicator_code,
                        region_code=region_code,
                        freq=freq,
                        trade_date=trade_date,
                        value=value,
                        source_code=source_code,
                        ingest_batch_id=batch_id
                    ))
                    inserted_count += 1
            
            # 第四步：分批插入新记录
            if records_to_insert:
                batch_size = 1000  # 每批插入1000条
                for i in range(0, len(records_to_insert), batch_size):
                    batch_records = records_to_insert[i:i + batch_size]
                    db.bulk_save_objects(batch_records)
                    db.flush()  # 每批flush一次，避免内存占用过大
            
            # 第五步：批量更新现有记录
            if records_to_update:
                batch_size = 1000  # 每批更新1000条
                for i in range(0, len(records_to_update), batch_size):
                    db.flush()  # 刷新更新
        
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
            "errors": [{"sheet": sheet_name, "reason": f"旧格式处理失败: {error_msg}"}]
        }


def _import_wide_table(db: Session, excel_file, sheet_name: str, batch_id: int, source_code: str = "YONGYI") -> Dict:
    """导入宽表（日期跨列）"""
    errors = []
    inserted_count = 0
    updated_count = 0
    
    try:
        # 使用宽表解析工具
        df_long = parse_wide_table_with_dates(
            excel_file,
            sheet_name,
            date_col_start=None,  # 自动识别
            header_rows=1,
            region_col=0
        )
        
        if df_long.empty:
            return {
                "inserted": 0,
                "updated": 0,
                "errors": [{"sheet": sheet_name, "reason": "宽表解析结果为空"}]
            }
        
        # 根据sheet_name和字段名解析指标代码
        # 这里简化处理，实际可能需要更复杂的映射逻辑
        indicator_code = resolve_indicator_code(sheet_name, "*")
        if not indicator_code:
            # 如果无法解析，尝试从sheet名称推断
            if "屠宰" in sheet_name:
                indicator_code = "slaughter_daily"
            elif "价格" in sheet_name:
                indicator_code = "hog_price_province"
            else:
                return {
                    "inserted": 0,
                    "updated": 0,
                    "errors": [{"sheet": sheet_name, "reason": f"无法解析指标代码"}]
                }
        
        # 获取或创建指标维度
        indicator = db.query(DimIndicator).filter(
            DimIndicator.indicator_code == indicator_code
        ).first()
        
        if not indicator:
            indicator = DimIndicator(
                indicator_code=indicator_code,
                indicator_name=indicator_code,
                freq="D",
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
                
                # 使用统一的区域映射服务（严格验证）
                region = get_or_create_region(db, region_name=region_name, strict=True)
                if not region:
                    # 跳过无效的区域名称（如"出栏价"、"均价"等）
                    errors.append({
                        "sheet": sheet_name,
                        "row": idx + 1,
                        "reason": f"无效的区域名称: {region_name}"
                    })
                    continue
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
                errors.append({
                    "sheet": sheet_name,
                    "row": idx + 1,
                    "reason": f"处理失败: {str(e)}"
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
