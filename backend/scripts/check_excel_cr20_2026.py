"""
检查Excel文件中是否有2026年的CR20数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_excel_cr20_2026():
    """检查Excel文件中是否有2026年的CR20数据"""
    print("=" * 80)
    print("检查Excel文件中是否有2026年的CR20数据")
    print("=" * 80)
    
    docs_dir = script_dir.parent / "docs"
    excel_files = list(docs_dir.glob("*集团企业*.xlsx"))
    
    if not excel_files:
        print("\n未找到集团企业月度数据跟踪文件")
        return
    
    file_path = excel_files[0]
    print(f"\n找到文件: {file_path.name}")
    
    try:
        # 读取"集团企业全国"sheet
        df = pd.read_excel(file_path, sheet_name="集团企业全国", header=None, engine='openpyxl')
        
        print(f"\nSheet形状: {df.shape}")
        print(f"\n前20行数据:")
        print(df.head(20).to_string())
        
        # 查找"实际出栏量"行
        print(f"\n查找'实际出栏量'行:")
        for idx, row in df.iterrows():
            # B列（索引1）是"实际出栏量"
            if pd.notna(row.iloc[1]) and str(row.iloc[1]) == "实际出栏量":
                print(f"\n找到在第{idx+1}行:")
                print(f"  日期列(A列，索引0): {row.iloc[0]}")
                print(f"  类型列(B列，索引1): {row.iloc[1]}")
                print(f"  CR20列(Y列，索引24): {row.iloc[24] if len(row) > 24 else 'N/A'}")
                
                # 检查后续几行
                print(f"\n后续10行数据:")
                for j in range(idx+1, min(len(df), idx+11)):
                    next_row = df.iloc[j]
                    date_val = next_row.iloc[0]
                    type_val = next_row.iloc[1]
                    cr20_val = next_row.iloc[24] if len(next_row) > 24 else None
                    
                    if pd.notna(date_val):
                        print(f"    行{j+1}: 日期={date_val}, 类型={type_val}, CR20={cr20_val}")
                        
                        # 检查是否是2026年的数据
                        if isinstance(date_val, (pd.Timestamp, datetime)):
                            if date_val.year == 2026:
                                print(f"      *** 这是2026年的数据！月份={date_val.month} ***")
                        elif isinstance(date_val, str):
                            if '2026' in str(date_val):
                                print(f"      *** 这是2026年的数据！ ***")
        
        # 检查所有日期列的值
        print(f"\n检查所有日期值（A列）:")
        date_col = df.iloc[:, 0]
        unique_dates = date_col.dropna().unique()
        print(f"  唯一日期数量: {len(unique_dates)}")
        
        # 查找2026年的日期
        print(f"\n查找2026年的日期:")
        for date_val in unique_dates:
            if isinstance(date_val, (pd.Timestamp, datetime)):
                if date_val.year == 2026:
                    print(f"  找到: {date_val}")
            elif isinstance(date_val, str):
                if '2026' in str(date_val):
                    print(f"  找到: {date_val}")
                    
    except Exception as e:
        print(f"读取失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from datetime import datetime
    check_excel_cr20_2026()
