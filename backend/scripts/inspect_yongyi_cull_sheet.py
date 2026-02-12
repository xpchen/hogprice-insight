"""查看 raw_table 中「月度-淘汰母猪屠宰厂宰杀量」前几行，确认日期与环比列。"""
# -*- coding: utf-8 -*-
import sys
import io
import json
from pathlib import Path
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

def main():
    db = SessionLocal()
    try:
        row = db.query(RawSheet).join(RawFile).filter(RawSheet.sheet_name == "月度-淘汰母猪屠宰厂宰杀量").first()
        if not row:
            print("未找到 sheet「月度-淘汰母猪屠宰厂宰杀量」")
            return
        rt = db.query(RawTable).filter(RawTable.raw_sheet_id == row.id).first()
        if not rt or not rt.table_json:
            print("raw_table 无数据")
            return
        data = rt.table_json if isinstance(rt.table_json, list) else json.loads(rt.table_json)
        print("文件:", row.raw_file.filename)
        print("行数:", len(data))
        print("前 8 行（每行前 18 列）:")
        for i, r in enumerate(data[:8]):
            part = list(r[:18]) if len(r) >= 18 else list(r)
            print(f"  行{i}: {part}")
        # 检查 col0 和 col12/col13
        if len(data) > 4:
            print("\n数据行示例（行4 列0=日期, 列12=宰杀量, 列13=环比）:")
            r = data[4]
            c12 = repr(r[12]) if len(r) > 12 else 'N/A'
            c13 = repr(r[13]) if len(r) > 13 else 'N/A'
            print(f"  col0={r[0]!r}, col12={c12}, col13={c13}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
