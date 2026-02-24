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
        模板类型：LH_FTR / LH_OPT / YONGYI_DAILY / YONGYI_WEEKLY / GANGLIAN_DAILY /
                 INDUSTRY_DATA / PREMIUM_DATA / ENTERPRISE_DAILY / ENTERPRISE_MONTHLY /
                 WHITE_STRIP_MARKET / LEGACY
    """
    filename_lower = filename.lower()
    filename_no_ext = filename.replace('.xlsx', '').replace('.xls', '')
    
    # 生猪产业数据（2、【生猪产业数据】.xlsx）：协会、NYB、统计局、供需曲线
    if '生猪产业数据' in filename_no_ext or '产业数据' in filename_no_ext:
        return "INDUSTRY_DATA"
    
    # 生猪期货升贴水（4.1、生猪期货升贴水数据（盘面结算价）.xlsx）
    if '升贴水' in filename_no_ext and ('盘面结算价' in filename_no_ext or '期货' in filename_no_ext):
        return "PREMIUM_DATA"
    
    # 集团企业出栏跟踪【分省区】（3.1、集团企业出栏跟踪【分省区】.xlsx）
    if '集团企业出栏跟踪' in filename_no_ext and '分省区' in filename_no_ext:
        return "ENTERPRISE_DAILY"
    
    # 集团企业月度数据跟踪（3.2、集团企业月度数据跟踪.xlsx）
    if '集团企业月度数据' in filename_no_ext or '集团企业月度' in filename_no_ext:
        return "ENTERPRISE_MONTHLY"
    
    # 白条市场跟踪（3.3、白条市场跟踪.xlsx）
    if '白条市场跟踪' in filename_no_ext or '白条市场' in filename_no_ext:
        return "WHITE_STRIP_MARKET"
    
    # 基于文件名判断（期货/期权需在产业数据之后判断，避免"期货升贴水"被误判）
    if 'lh_ftr' in filename_lower or ('期货' in filename_no_ext and '升贴水' not in filename_no_ext):
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
        
        # 生猪产业数据：NYB、02.协会猪料、供需曲线、03.统计局、A1供给预测 等
        industry_sheets = ['NYB', '02.协会猪料', '供需曲线', '03.统计局', 'A1供给预测', '4.2涌益底稿', '涌益样本']
        if any(any(s in name for s in industry_sheets) for name in sheet_names):
            return "INDUSTRY_DATA"
        
        # 升贴水：期货结算价(1月交割连续)_生猪 等
        if any('期货结算价' in name and '生猪' in name for name in sheet_names):
            return "PREMIUM_DATA"
        
        # 集团企业出栏【分省区】：CR5日度 等
        if any('CR5日度' in name or '西南汇总' in name for name in sheet_names):
            return "ENTERPRISE_DAILY"
        
        # 集团企业月度：集团企业全国、汇总 等
        if any('集团企业全国' in name or name == '汇总' for name in sheet_names):
            return "ENTERPRISE_MONTHLY"
        
        # 白条市场：白条市场、华宝和牧原白条 等
        if any('白条市场' in name or '华宝和牧原白条' in name for name in sheet_names):
            return "WHITE_STRIP_MARKET"
        
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
