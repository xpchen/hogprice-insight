"""期权导入器（lh_opt.xlsx）"""
import pandas as pd
from io import BytesIO
from typing import Dict, List
from sqlalchemy.orm import Session

from app.models import FactOptionsDaily, DimOption
from app.utils.value_cleaner import clean_numeric_value
from app.utils.contract_parser import parse_option_contract


def import_lh_opt(db: Session, file_content: bytes, batch_id: int) -> Dict:
    """
    导入期权日历史数据（lh_opt.xlsx）
    
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
        # 读取Excel文件
        excel_file = pd.ExcelFile(BytesIO(file_content), engine='openpyxl')
        
        # 查找"日历史行情"sheet
        sheet_name = None
        for name in excel_file.sheet_names:
            if '日历史' in name or '历史行情' in name:
                sheet_name = name
                break
        
        if not sheet_name:
            raise ValueError("未找到'日历史行情'sheet")
        
        # 读取数据
        df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
        
        # 识别列名（可能包含中文字段名）
        column_mapping = {
            '商品名称': 'instrument',
            '合约名称': 'option_code',
            '交易日期': 'trade_date',
            '开盘价': 'open',
            '最高价': 'high',
            '最低价': 'low',
            '收盘价': 'close',
            '前结算价': 'pre_settle',
            '结算价': 'settle',
            '涨跌': 'chg',
            '涨跌1': 'chg1',
            'Delta': 'delta',
            '隐含波动率(%)': 'iv',
            '成交量': 'volume',
            '持仓量': 'open_interest',
            '持仓量变化': 'oi_chg',
            '成交额': 'turnover',
            '行权量': 'exercise_volume'
        }
        
        # 重命名列
        df_renamed = df.rename(columns=column_mapping)
        
        # 处理每一行
        records_to_insert = []
        
        for idx, row in df_renamed.iterrows():
            try:
                # 解析期权合约代码
                option_code = str(row.get('option_code', '')).strip()
                if not option_code or option_code.lower() == 'nan':
                    continue
                
                option_info = parse_option_contract(option_code)
                underlying_contract = option_info['underlying_contract']
                option_type = option_info['option_type']
                strike = option_info['strike']
                instrument = underlying_contract[:2].upper()  # 从标的合约提取品种代码
                
                # 解析日期
                trade_date_val = row.get('trade_date')
                if pd.isna(trade_date_val):
                    errors.append({
                        "row": idx + 2,
                        "reason": "交易日期为空"
                    })
                    continue
                
                # 处理日期：支持YYYYMMDD格式（8位数字）
                trade_date_parsed = None
                if isinstance(trade_date_val, (int, float)):
                    # 如果是数字，尝试解析为YYYYMMDD格式
                    date_str = str(int(trade_date_val))
                    if len(date_str) == 8:
                        try:
                            from datetime import datetime
                            trade_date_parsed = datetime.strptime(date_str, '%Y%m%d')
                        except ValueError:
                            pass
                
                # 如果数字解析失败，尝试pandas解析
                if trade_date_parsed is None:
                    trade_date_parsed = pd.to_datetime(trade_date_val, errors='coerce', format='%Y%m%d')
                
                # 如果还是失败，尝试通用解析
                if pd.isna(trade_date_parsed):
                    trade_date_parsed = pd.to_datetime(trade_date_val, errors='coerce')
                
                if pd.isna(trade_date_parsed):
                    errors.append({
                        "row": idx + 2,
                        "reason": f"交易日期解析失败: {trade_date_val}"
                    })
                    continue
                
                trade_date = trade_date_parsed.date()
                
                # 检查日期是否合理（不能是1970年，这通常是解析失败的默认值）
                if trade_date.year < 2000 or trade_date.year > 2100:
                    errors.append({
                        "row": idx + 2,
                        "reason": f"交易日期不合理: {trade_date} (原始值: {trade_date_val})"
                    })
                    continue
                
                # 清洗数值字段
                open_price = clean_numeric_value(row.get('open'))
                high_price = clean_numeric_value(row.get('high'))
                low_price = clean_numeric_value(row.get('low'))
                close_price = clean_numeric_value(row.get('close'))
                pre_settle_price = clean_numeric_value(row.get('pre_settle'))
                settle_price = clean_numeric_value(row.get('settle'))
                chg = clean_numeric_value(row.get('chg'))
                chg1 = clean_numeric_value(row.get('chg1'))
                delta = clean_numeric_value(row.get('delta'))
                iv = clean_numeric_value(row.get('iv'))  # IV保持百分比数值（如23.18）
                volume = clean_numeric_value(row.get('volume'))
                open_interest = clean_numeric_value(row.get('open_interest'))
                oi_chg = clean_numeric_value(row.get('oi_chg'))
                turnover = clean_numeric_value(row.get('turnover'))
                exercise_volume = clean_numeric_value(row.get('exercise_volume'))
                
                # 检查是否已存在
                existing = db.query(FactOptionsDaily).filter(
                    FactOptionsDaily.option_code == option_code,
                    FactOptionsDaily.trade_date == trade_date
                ).first()
                
                record_data = {
                    'instrument': instrument,
                    'underlying_contract': underlying_contract,
                    'option_type': option_type,
                    'strike': strike,
                    'option_code': option_code,
                    'trade_date': trade_date,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'pre_settle': pre_settle_price,
                    'settle': settle_price,
                    'chg': chg,
                    'chg1': chg1,
                    'delta': delta,
                    'iv': iv,
                    'volume': int(volume) if volume else None,
                    'open_interest': int(open_interest) if open_interest else None,
                    'oi_chg': int(oi_chg) if oi_chg else None,
                    'turnover': turnover,
                    'exercise_volume': int(exercise_volume) if exercise_volume else None,
                    'ingest_batch_id': batch_id
                }
                
                if existing:
                    # 更新现有记录
                    for key, value in record_data.items():
                        setattr(existing, key, value)
                    updated_count += 1
                else:
                    # 插入新记录
                    records_to_insert.append(FactOptionsDaily(**record_data))
                    inserted_count += 1
                
                # Upsert期权维度表（如果不存在则创建，存在则跳过）
                option_dim = db.query(DimOption).filter(
                    DimOption.option_code == option_code.lower()  # 统一使用小写查询
                ).first()
                
                if not option_dim:
                    try:
                        option_dim = DimOption(
                            underlying_contract=underlying_contract,
                            option_type=option_type,
                            strike=strike,
                            option_code=option_code.lower()  # 统一使用小写存储
                        )
                        db.add(option_dim)
                        db.flush()  # 立即刷新，如果重复则抛出异常
                    except Exception:
                        # 如果插入失败（可能是并发插入导致的重复），回滚并查询
                        db.rollback()
                        option_dim = db.query(DimOption).filter(
                            DimOption.option_code == option_code.lower()
                        ).first()
                        if not option_dim:
                            # 如果还是不存在，重新添加
                            option_dim = DimOption(
                                underlying_contract=underlying_contract,
                                option_type=option_type,
                                strike=strike,
                                option_code=option_code.lower()
                            )
                            db.add(option_dim)
                            db.flush()
                
            except Exception as e:
                # 截断过长的错误消息
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:197] + "..."
                errors.append({
                    "row": idx + 2,
                    "reason": f"处理失败: {error_msg}"
                })
                continue
        
        # 批量插入
        if records_to_insert:
            db.bulk_save_objects(records_to_insert)
        
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
