"""模板识别服务"""
from typing import Optional
from io import BytesIO
import pandas as pd
from openpyxl import load_workbook


def detect_template(file_content: bytes, filename: str) -> str:
    """
    识别模板类型
    
    Args:
        file_content: Excel文件内容（bytes）
        filename: 文件名
    
    Returns:
        模板类型：LH_FTR / LH_OPT / YONGYI_DAILY / YONGYI_WEEKLY / GANGLIAN_DAILY / LEGACY
    """
    filename_lower = filename.lower()
    
    # 基于文件名判断
    if 'lh_ftr' in filename_lower or '期货' in filename_lower:
        return "LH_FTR"
    elif 'lh_opt' in filename_lower or '期权' in filename_lower:
        return "LH_OPT"
    elif '涌益' in filename_lower and '日度' in filename_lower:
        return "YONGYI_DAILY"
    elif '涌益' in filename_lower and '周度' in filename_lower:
        return "YONGYI_WEEKLY"
    
    # 基于sheet名称和内容判断
    try:
        excel_file = pd.ExcelFile(BytesIO(file_content), engine='openpyxl')
        sheet_names = excel_file.sheet_names
        
        # 检查是否有"日历史行情"sheet（期货/期权）
        for sheet_name in sheet_names:
            if '日历史' in sheet_name or '历史行情' in sheet_name:
                # 读取第一行判断字段
                df_sample = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=2, engine='openpyxl')
                columns = df_sample.columns.tolist()
                
                # 检查是否包含期权特有字段
                if any('delta' in str(col).lower() or 'iv' in str(col).lower() or '行权' in str(col) for col in columns):
                    return "LH_OPT"
                elif any('合约' in str(col) for col in columns):
                    return "LH_FTR"
        
        # 优先检查是否是钢联数据格式（与涌益区分开）
        # 特征：第1行是"钢联数据"，第2行是指标名称，第3行是单位，第4行是更新时间，第5行开始是数据
        ganglian_format_found = False
        for sheet_name in sheet_names:
            try:
                df_sample = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=5, header=None, engine='openpyxl')
                # 检查第1行第1列是否是"钢联数据"
                if df_sample.shape[0] >= 1 and str(df_sample.iloc[0, 0]).strip() == '钢联数据':
                    ganglian_format_found = True
                    break
            except:
                continue
        
        if ganglian_format_found:
            return "GANGLIAN_DAILY"  # 钢联日度数据（独立数据源）
        
        # 检查是否有"周度"相关sheet（但排除旧格式）
        if any('周度' in name for name in sheet_names):
            return "YONGYI_WEEKLY"
        
        # 检查是否有涌益日度特征sheet
        if any('价格' in name or '屠宰' in name or '价差' in name for name in sheet_names):
            return "YONGYI_DAILY"
        
    except Exception:
        pass
    
    # 默认返回LEGACY（旧格式）
    return "LEGACY"
