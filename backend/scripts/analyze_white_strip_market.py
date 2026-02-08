"""
分析白条市场跟踪Excel文件结构
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze_white_strip_market():
    """分析白条市场跟踪文件"""
    print("=" * 80)
    print("分析白条市场跟踪Excel文件")
    print("=" * 80)
    
    docs_dir = script_dir.parent / "docs" / "生猪"
    file_path = docs_dir / "3.3、白条市场跟踪.xlsx"
    
    if not file_path.exists():
        print(f"\n文件不存在: {file_path}")
        return
    
    print(f"\n找到文件: {file_path.name}")
    
    try:
        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_names = excel_file.sheet_names
        
        print(f"\n所有sheet名称 ({len(sheet_names)}个):")
        for idx, name in enumerate(sheet_names, 1):
            print(f"  {idx}. {name}")
        
        # 查找"白条市场"sheet
        if "白条市场" in sheet_names:
            print(f"\n分析'白条市场'sheet:")
            df = pd.read_excel(file_path, sheet_name="白条市场", header=None, engine='openpyxl')
            
            print(f"\nSheet形状: {df.shape}")
            print(f"\n前30行数据:")
            print(df.head(30).to_string())
            
            # 查找表头行
            print(f"\n查找表头行:")
            for idx, row in df.iterrows():
                row_str = ' '.join([str(x) for x in row if pd.notna(x)])
                if any(keyword in row_str for keyword in ['日期', '市场', '到货量', '价格', '白条']):
                    print(f"  行{idx}: {row.tolist()[:20]}")
            
            # 查找数据行
            print(f"\n查找数据行（前10行）:")
            for idx in range(min(10, len(df))):
                row = df.iloc[idx]
                non_null_count = row.notna().sum()
                if non_null_count > 3:  # 至少有3个非空值
                    print(f"  行{idx}: {row.tolist()[:15]}")
        else:
            print("\n未找到'白条市场'sheet，分析第一个sheet:")
            df = pd.read_excel(file_path, sheet_name=sheet_names[0], header=None, engine='openpyxl')
            print(f"\nSheet形状: {df.shape}")
            print(f"\n前30行数据:")
            print(df.head(30).to_string())
            
    except Exception as e:
        print(f"读取失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_white_strip_market()
