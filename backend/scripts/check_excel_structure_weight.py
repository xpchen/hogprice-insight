"""检查Excel中周度-体重的实际结构"""
import sys
import os
import io

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from pathlib import Path

def check_excel_structure():
    """检查Excel中周度-体重的实际结构"""
    print("=" * 80)
    print("检查Excel中周度-体重的实际结构")
    print("=" * 80)
    
    # 查找Excel文件
    excel_files = list(Path("docs").glob("*涌益咨询 周度数据*.xlsx"))
    if not excel_files:
        print("❌ 未找到Excel文件")
        return
    
    excel_file = excel_files[0]
    print(f"✓ 找到Excel文件: {excel_file}")
    
    try:
        # 读取"周度-体重"sheet
        df = pd.read_excel(excel_file, sheet_name="周度-体重", header=None, engine='openpyxl')
        
        print(f"\nExcel结构（前20行，前30列）:")
        print(df.iloc[:20, :30].to_string())
        
        # 检查第0行（第一行），查找"全国2"
        print(f"\n第0行（第一行，查找'全国2'）:")
        for idx, val in enumerate(df.iloc[0]):
            val_str = str(val).strip() if pd.notna(val) else ""
            if "全国2" in val_str or "全国 2" in val_str:
                print(f"  列{idx}: {val_str}")
                # 检查这一列在第1行（表头行）的值
                if idx < len(df.iloc[1]):
                    header_val = df.iloc[1, idx]
                    print(f"    对应的表头（第1行）: {header_val}")
        
        # 检查第2行（header_row=2，索引为1）
        print(f"\n第2行（header_row=2，索引为1）:")
        print(df.iloc[1, :15].tolist())
        
        # 检查第3行（数据开始行）
        print(f"\n第3行（数据开始行，索引为2）:")
        print(df.iloc[2, :15].tolist())
        
        # 查找"指标"列
        print(f"\n查找'指标'列:")
        indicator_col_idx = None
        for idx, col in enumerate(df.iloc[1]):
            if str(col).strip() == "指标":
                indicator_col_idx = idx
                print(f"  ✓ 找到'指标'列，索引: {idx}")
                print(f"    所有行的值（查找'90kg以下'和'150kg以上'）:")
                indicators = set()
                for row_idx in range(2, len(df)):
                    value = df.iloc[row_idx, idx]
                    value_str = str(value).strip()
                    indicators.add(value_str)
                    if "90kg" in value_str.lower() or "150kg" in value_str.lower() or "90" in value_str or "150" in value_str:
                        print(f"      行{row_idx}: {value}")
                print(f"    所有不同的指标值（前20个）: {sorted(list(indicators))[:20]}")
                break
        
        # 查找"全国2"列（检查所有可能的列名）
        print(f"\n查找'全国2'列:")
        nation2_col_idx = None
        print(f"  所有列名（前30个）:")
        for idx, col in enumerate(df.iloc[1][:30]):
            col_str = str(col).strip()
            print(f"    列{idx}: {col_str}")
            if "全国2" in col_str or "全国 2" in col_str or col_str == "全国2":
                nation2_col_idx = idx
                print(f"  ✓ 找到'全国2'列，索引: {idx}")
                break
        
        # 如果没找到，检查所有列
        if nation2_col_idx is None:
            print(f"  检查所有列名（查找包含'全国'的列）:")
            for idx, col in enumerate(df.iloc[1]):
                col_str = str(col).strip()
                if "全国" in col_str or (pd.notna(col) and "全国" in str(col)):
                    print(f"    列{idx}: {col_str}")
                    if "2" in col_str or col_str.endswith("2") or str(col).endswith("2"):
                        nation2_col_idx = idx
                        print(f"  ✓ 找到可能的'全国2'列，索引: {idx}")
            
            # 如果还是没找到，打印所有列名
            if nation2_col_idx is None:
                print(f"\n  所有列名（完整列表）:")
                for idx, col in enumerate(df.iloc[1]):
                    print(f"    列{idx}: {repr(col)}")
        
        # 如果找到了"指标"列和"全国2"列，显示它们的关系
        if indicator_col_idx is not None and nation2_col_idx is not None:
            print(f"\n'指标'列和'全国2'列的关系（查找'90kg以下'和'150kg以上'）:")
            for row_idx in range(2, min(len(df), 1000)):
                indicator = df.iloc[row_idx, indicator_col_idx]
                value = df.iloc[row_idx, nation2_col_idx]
                if str(indicator).strip() in ["90kg以下", "150kg以上"]:
                    print(f"  行{row_idx}: indicator={indicator}, 全国2列的值={value} (类型: {type(value).__name__})")
                    if row_idx > 100:  # 只显示前100个匹配的行
                        break
        
        # 检查是否有"90kg以下"或"150kg以上"作为列名
        print(f"\n检查列名中是否有'90kg以下'或'150kg以上':")
        for idx, col in enumerate(df.iloc[1]):
            col_str = str(col).strip()
            if "90kg" in col_str.lower() or "150kg" in col_str.lower() or "90" in col_str or "150" in col_str:
                print(f"  列{idx}: {col_str}")
        
    except Exception as e:
        print(f"\n❌ 读取Excel失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_excel_structure()
