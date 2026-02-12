# -*- coding: utf-8 -*-
"""打印 华宝和牧原白条 sheet 前两行表头，并模拟解析器列匹配，排查华东缺失原因"""
import sys
import io
from pathlib import Path

script_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(script_dir))
if sys.stdout.encoding and sys.stdout.encoding.upper() != 'UTF-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd

def main():
    project_root = script_dir.parent
    file_path = project_root / "docs" / "生猪" / "3.3、白条市场跟踪.xlsx"
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return

    df = pd.read_excel(file_path, sheet_name="华宝和牧原白条", header=None, engine='openpyxl')
    row0 = df.iloc[0].tolist()
    row1 = df.iloc[1].tolist() if len(df) > 1 else []

    print("=== 第0行（header_row=0）===")
    for i, v in enumerate(row0):
        print(f"  col[{i}]: {repr(v)}")
    print("\n=== 第1行（sub_header_row=1）===")
    for i, v in enumerate(row1):
        print(f"  col[{i}]: {repr(v)}")

    # 模拟 parser 的 header_per_col
    header_per_col = []
    for col_idx in range(len(row0)):
        prim = row0[col_idx] if col_idx < len(row0) else None
        sub = row1[col_idx] if col_idx < len(row1) else None
        prim_str = str(prim).strip() if prim is not None and pd.notna(prim) and str(prim).strip() else ""
        sub_str = str(sub).strip() if sub is not None and pd.notna(sub) and str(sub).strip() else ""
        header_per_col.append(sub_str if sub_str else prim_str)

    print("\n=== header_per_col（解析器实际用于匹配的每列文本）===")
    for i, t in enumerate(header_per_col):
        print(f"  col[{i}]: {repr(t)}")

    patterns = ["华宝肉条", "牧原白条", "华东", "河南山东", "湖北陕西", "京津冀", "东北"]
    metric_keys = [
        "WHITE_STRIP_PRICE_HUABAO",
        "WHITE_STRIP_PRICE_MUYUAN",
        "WHITE_STRIP_PRICE_EAST_CHINA",
        "WHITE_STRIP_PRICE_HENAN_SHANDONG",
        "WHITE_STRIP_PRICE_HUBEI_SHANXI",
        "WHITE_STRIP_PRICE_JINGJINJI",
        "WHITE_STRIP_PRICE_NORTHEAST",
    ]
    column_metric_map = {}
    print("\n=== 模拟列匹配（pattern in header_per_col[col]）===")
    for pattern, key in zip(patterns, metric_keys):
        for col_idx, col_name in enumerate(header_per_col):
            if col_idx in column_metric_map:
                continue
            if col_name and pattern in col_name:
                column_metric_map[col_idx] = key
                print(f"  {pattern} -> col[{col_idx}] (header_per_col={repr(col_name)}) -> {key}")
                break
        else:
            for col_idx, col_name in enumerate(row0):
                if col_idx in column_metric_map:
                    continue
                cn = str(col_name).strip() if col_name is not None and pd.notna(col_name) else ""
                if cn and pattern in cn:
                    column_metric_map[col_idx] = key
                    print(f"  {pattern} -> col[{col_idx}] (row0={repr(cn)}) -> {key}")
                    break
            else:
                print(f"  {pattern} -> 未匹配到任何列 -> {key}")

    print("\n=== 包含「华东」的列（任意行）===")
    for i, t in enumerate(header_per_col):
        if "华东" in t:
            print(f"  header_per_col[{i}] = {repr(t)}")
    for i, v in enumerate(row0):
        if v and "华东" in str(v):
            print(f"  row0[{i}] = {repr(v)}")
    for i, v in enumerate(row1):
        if v and "华东" in str(v):
            print(f"  row1[{i}] = {repr(v)}")

if __name__ == "__main__":
    main()
