"""
检查集团价格功能的数据源
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_ganglian_group_price():
    """检查钢联模板的集团企业出栏价sheet"""
    print("=" * 80)
    print("1. 检查钢联模板的'集团企业出栏价'sheet")
    print("=" * 80)
    
    docs_dir = script_dir.parent / "docs"
    ganglian_files = list(docs_dir.glob("*钢联*.xlsx"))
    
    if ganglian_files:
        file_path = ganglian_files[0]
        print(f"\n找到文件: {file_path.name}")
        
        try:
            excel_file = pd.ExcelFile(file_path, engine='openpyxl')
            sheet_names = excel_file.sheet_names
            print(f"\n所有sheet名称: {sheet_names}")
            
            if "集团企业出栏价" in sheet_names:
                df = pd.read_excel(file_path, sheet_name="集团企业出栏价", header=None, engine='openpyxl')
                
                print(f"\nSheet形状: {df.shape}")
                print(f"\n前20行数据:")
                print(df.head(20).to_string())
                
                # 查找企业名称行
                print(f"\n查找企业名称行:")
                for idx, row in df.iterrows():
                    row_str = ' '.join([str(x) for x in row if pd.notna(x)])
                    if any(company in row_str for company in ['吉林中粮', '河南牧原', '山东新希望', '广东温氏', '湖南唐人神', '江西温氏', '四川德康', '贵州富之源', '华宝白条', '牧原白条']):
                        print(f"  行{idx}: {row.tolist()[:15]}")
            else:
                print("\n未找到'集团企业出栏价'sheet")
        except Exception as e:
            print(f"读取失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("未找到钢联文件")

def check_white_strip_market():
    """检查白条市场跟踪的白条市场sheet"""
    print("\n" + "=" * 80)
    print("2. 检查白条市场跟踪的'白条市场'sheet")
    print("=" * 80)
    
    docs_dir = script_dir.parent / "docs"
    # 查找包含"白条"或"市场"的文件
    market_files = []
    for pattern in ["*白条*", "*市场*", "*跟踪*"]:
        market_files.extend(list(docs_dir.glob(f"{pattern}.xlsx")))
    
    if market_files:
        print(f"\n找到 {len(market_files)} 个相关文件:")
        for f in market_files:
            print(f"  - {f.name}")
        
        # 尝试读取每个文件
        for file_path in market_files[:3]:  # 只检查前3个
            try:
                excel_file = pd.ExcelFile(file_path, engine='openpyxl')
                sheet_names = excel_file.sheet_names
                
                if "白条市场" in sheet_names:
                    print(f"\n在文件 {file_path.name} 中找到'白条市场'sheet")
                    df = pd.read_excel(file_path, sheet_name="白条市场", header=None, engine='openpyxl', nrows=20)
                    
                    print(f"\nSheet形状: {df.shape}")
                    print(f"\n前20行数据:")
                    print(df.head(20).to_string())
                    break
            except Exception as e:
                continue
    else:
        print("未找到白条市场相关文件")

if __name__ == "__main__":
    check_ganglian_group_price()
    check_white_strip_market()
