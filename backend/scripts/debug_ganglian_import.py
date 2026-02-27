"""Debug: check 钢联 Excel structure and meta flow"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

import pandas as pd

def main():
    path = project_root / "docs" / "0226" / "生猪" / "1、价格：钢联自动更新模板.xlsx"
    out_path = project_root / "backend" / "excel_debug_out.txt"
    lines = []
    def log(s):
        lines.append(s)
    if not path.exists():
        log(f"File not found: {path}")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return
    xl = pd.ExcelFile(path)
    for sn in xl.sheet_names[:2]:
        df = pd.read_excel(xl, sheet_name=sn, header=None, nrows=6)
        log(f"\n=== Sheet: {sn} ===")
        for i in range(min(6, len(df))):
            row_vals = []
            for j in range(min(4, df.shape[1])):
                v = df.iloc[i, j]
                s = str(v)[:35] if pd.notna(v) else "NaN"
                row_vals.append(s)
            log(f"  Row {i} (1-based {i+1}): {row_vals}")
        if len(df) >= 4:
            update_row = df.iloc[3]
            sample = update_row.iloc[1] if len(update_row) > 1 else update_row.iloc[0]
            log(f"  Row 4 (update_time_row) sample: {sample}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote", out_path)

if __name__ == "__main__":
    main()
