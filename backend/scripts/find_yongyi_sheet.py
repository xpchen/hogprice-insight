"""
查找涌益文件中的"商品猪"sheet
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def find_yongyi_sheets():
    """查找涌益文件中的所有sheet"""
    print("=" * 80)
    print("查找涌益文件中的sheet")
    print("=" * 80)
    
    docs_dir = script_dir.parent / "docs"
    yongyi_files = list(docs_dir.glob("*涌益*周度数据*.xlsx"))
    
    if yongyi_files:
        file_path = yongyi_files[0]
        print(f"\n找到文件: {file_path.name}")
        
        try:
            excel_file = pd.ExcelFile(file_path, engine='openpyxl')
            sheet_names = excel_file.sheet_names
            
            print(f"\n所有sheet名称 ({len(sheet_names)}个):")
            for idx, name in enumerate(sheet_names, 1):
                print(f"  {idx}. {name}")
            
            # 查找包含"商品猪"的sheet
            print(f"\n包含'商品猪'的sheet:")
            matching_sheets = [s for s in sheet_names if '商品猪' in s]
            if matching_sheets:
                for sheet_name in matching_sheets:
                    print(f"  - {sheet_name}")
                    
                    # 读取该sheet的前几行
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='openpyxl', nrows=10)
                    print(f"\n    Sheet形状: {df.shape}")
                    print(f"    前10行数据:")
                    print(df.to_string())
                    print()
            else:
                print("  未找到包含'商品猪'的sheet")
            
            # 查找包含"月度"的sheet
            print(f"\n包含'月度'的sheet:")
            monthly_sheets = [s for s in sheet_names if '月度' in s]
            if monthly_sheets:
                for sheet_name in monthly_sheets:
                    print(f"  - {sheet_name}")
            else:
                print("  未找到包含'月度'的sheet")
                
        except Exception as e:
            print(f"读取失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("未找到涌益周度数据文件")

if __name__ == "__main__":
    find_yongyi_sheets()
