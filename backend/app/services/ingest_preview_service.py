"""导入预览服务"""
from typing import Dict, List, Optional
from io import BytesIO
import pandas as pd
import numpy as np
import warnings
from openpyxl import load_workbook

from app.services.ingest_template_detector import detect_template

# 抑制 openpyxl 的默认样式警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl.styles.stylesheet')
# 抑制 pandas 的纳秒转换警告
warnings.filterwarnings('ignore', message='Discarding nonzero nanoseconds in conversion')


def preview_excel(file_content: bytes, template_type: Optional[str] = None, filename: str = "") -> Dict:
    """
    预览Excel导入结果（不实际入库）
    
    Args:
        file_content: Excel文件内容（bytes）
        template_type: 模板类型（如果为None则自动识别）
        filename: 文件名（用于识别模板类型）
    
    Returns:
        {
            "template_type": str,
            "sheets": List[Dict],
            "date_range": {"start": str, "end": str},
            "sample_rows": List[Dict],
            "field_mappings": Dict
        }
    """
    if template_type is None:
        template_type = detect_template(file_content, filename)
    
    try:
        excel_file = pd.ExcelFile(BytesIO(file_content), engine='openpyxl')
        sheet_names = excel_file.sheet_names
        
        sheets_info = []
        all_dates = []
        sample_rows = []
        
        for sheet_name in sheet_names:
            try:
                # 读取前几行作为预览
                df_sample = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=10, engine='openpyxl')
                
                # 转换sample_data，确保数值类型正确
                sample_data = df_sample.head(5).to_dict('records')
                # 清理数据：将numpy类型转换为Python原生类型
                cleaned_sample_data = []
                for row in sample_data:
                    cleaned_row = {}
                    for key, value in row.items():
                        try:
                            # 处理pandas/numpy类型
                            if pd.isna(value):
                                cleaned_row[str(key)] = None
                            elif isinstance(value, pd.Timestamp):
                                cleaned_row[str(key)] = value.strftime("%Y-%m-%d")
                            elif isinstance(value, np.integer):
                                cleaned_row[str(key)] = int(value)
                            elif isinstance(value, np.floating):
                                # 如果是整数类型的float，转换为int
                                if value.is_integer():
                                    cleaned_row[str(key)] = int(value)
                                else:
                                    cleaned_row[str(key)] = float(value)
                            elif isinstance(value, np.bool_):
                                cleaned_row[str(key)] = bool(value)
                            elif isinstance(value, (int, float)):
                                # 如果是整数类型的float，转换为int
                                if isinstance(value, float) and value.is_integer():
                                    cleaned_row[str(key)] = int(value)
                                else:
                                    cleaned_row[str(key)] = value
                            else:
                                # 其他类型转为字符串
                                cleaned_row[str(key)] = str(value) if value is not None else None
                        except Exception as e:
                            # 如果转换失败，转为字符串
                            cleaned_row[str(key)] = str(value) if value is not None else None
                    cleaned_sample_data.append(cleaned_row)
                
                sheet_info = {
                    "name": sheet_name,
                    "rows": int(len(df_sample)),
                    "columns": [str(col) for col in df_sample.columns.tolist()],
                    "sample_data": cleaned_sample_data
                }
                sheets_info.append(sheet_info)
                
                # 尝试识别日期列
                for col in df_sample.columns:
                    if '日期' in str(col) or 'date' in str(col).lower():
                        dates = pd.to_datetime(df_sample[col], errors='coerce').dropna()
                        if not dates.empty:
                            # 转换为Python datetime对象
                            for d in dates:
                                if pd.notna(d):
                                    if isinstance(d, pd.Timestamp):
                                        # 转换为Python datetime（警告已被全局抑制）
                                        all_dates.append(d.to_pydatetime())
                                    else:
                                        all_dates.append(d)
                        break
                
            except Exception as e:
                sheets_info.append({
                    "name": sheet_name,
                    "error": str(e)
                })
        
        # 计算日期范围
        date_range = None
        if all_dates:
            # 过滤掉None值并确保是datetime类型
            valid_dates = []
            for d in all_dates:
                if d is not None:
                    try:
                        if isinstance(d, pd.Timestamp):
                            valid_dates.append(d.to_pydatetime())
                        elif hasattr(d, 'strftime'):
                            valid_dates.append(d)
                    except:
                        pass
            
            if valid_dates:
                try:
                    min_date = min(valid_dates)
                    max_date = max(valid_dates)
                    # 确保是datetime对象（警告已被全局抑制）
                    if isinstance(min_date, pd.Timestamp):
                        min_date = min_date.to_pydatetime()
                    if isinstance(max_date, pd.Timestamp):
                        max_date = max_date.to_pydatetime()
                    
                    date_range = {
                        "start": min_date.strftime("%Y-%m-%d") if hasattr(min_date, 'strftime') else str(min_date)[:10],
                        "end": max_date.strftime("%Y-%m-%d") if hasattr(max_date, 'strftime') else str(max_date)[:10]
                    }
                except Exception as e:
                    # 如果日期处理失败，跳过
                    pass
        
        return {
            "template_type": template_type,
            "sheets": sheets_info,
            "date_range": date_range,
            "sample_rows": sample_rows[:10],  # 最多10行样本
            "field_mappings": {}  # 字段映射将在实际导入时确定
        }
        
    except Exception as e:
        return {
            "template_type": template_type,
            "error": f"预览失败: {str(e)}",
            "sheets": [],
            "date_range": None,
            "sample_rows": [],
            "field_mappings": {}
        }
