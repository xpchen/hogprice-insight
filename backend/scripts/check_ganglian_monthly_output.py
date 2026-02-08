"""
检查钢联月度数据sheet中的出栏数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

docs_dir = script_dir.parent / "docs"
ganglian_files = list(docs_dir.glob("*钢联自动更新模板*.xlsx"))

if ganglian_files:
    file_path = ganglian_files[0]
    print(f"找到文件: {file_path.name}")
    
    try:
        df = pd.read_excel(file_path, sheet_name="月度数据", header=None, engine='openpyxl')
        
        print(f"\nSheet形状: {df.shape}")
        print(f"\n前20行数据:")
        print(df.head(20).to_string())
        
        # 查找包含"出栏"的列
        print(f"\n查找包含'出栏'的列:")
        if len(df) > 1:
            header_row = df.iloc[1].tolist() if len(df) > 1 else []
            print(f"第2行（指标名称）: {header_row}")
            
            # 查找包含"出栏"的列
            output_cols = []
            for idx, val in enumerate(header_row):
                if val and isinstance(val, str):
                    if '出栏' in val:
                        output_cols.append((idx, val))
                        print(f"  列{idx}: {val}")
                        # 显示该列的数据示例
                        if len(df) > 4:
                            col_data = df.iloc[4:15, idx].tolist()
                            print(f"    数据示例: {col_data}")
        
        # 检查是否有"全国"、"规模场"、"中小散户"相关的列
        print(f"\n查找'全国'、'规模场'、'中小散户'相关列:")
        for idx, val in enumerate(header_row):
            if val and isinstance(val, str):
                if '全国' in val or '规模场' in val or '中小散' in val or '中小散户' in val:
                    print(f"  列{idx}: {val}")
                    if len(df) > 4:
                        col_data = df.iloc[4:15, idx].tolist()
                        print(f"    数据示例: {col_data}")
        
    except Exception as e:
        print(f"读取失败: {e}")
        import traceback
        traceback.print_exc()
