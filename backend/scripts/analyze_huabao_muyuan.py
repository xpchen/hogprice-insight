"""
分析华宝和牧原白条sheet
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze_huabao_muyuan():
    """分析华宝和牧原白条sheet"""
    print("=" * 80)
    print("分析'华宝和牧原白条'sheet")
    print("=" * 80)
    
    docs_dir = script_dir.parent / "docs" / "生猪"
    file_path = docs_dir / "3.3、白条市场跟踪.xlsx"
    
    if not file_path.exists():
        print(f"\n文件不存在: {file_path}")
        return
    
    try:
        df = pd.read_excel(file_path, sheet_name="华宝和牧原白条", header=None, engine='openpyxl')
        
        print(f"\nSheet形状: {df.shape}")
        print(f"\n前30行数据:")
        print(df.head(30).to_string())
        
        # 查找表头行
        print(f"\n查找表头行:")
        for idx, row in df.iterrows():
            row_str = ' '.join([str(x) for x in row if pd.notna(x)])
            if any(keyword in row_str for keyword in ['日期', '华宝', '牧原', '白条', '价格']):
                print(f"  行{idx}: {row.tolist()[:20]}")
                
    except Exception as e:
        print(f"读取失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_huabao_muyuan()
