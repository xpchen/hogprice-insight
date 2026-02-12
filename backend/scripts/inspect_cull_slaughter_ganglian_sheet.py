"""查看 raw_table 中「淘汰母猪屠宰」sheet 的表结构（前几行），便于 API 取数列索引。"""
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
        row = db.query(RawSheet).join(RawFile).filter(RawSheet.sheet_name == "淘汰母猪屠宰").first()
        if not row:
            print("未找到 sheet「淘汰母猪屠宰」")
            return
        rt = db.query(RawTable).filter(RawTable.raw_sheet_id == row.id).first()
        if not rt or not rt.table_json:
            print("raw_table 无数据")
            return
        data = rt.table_json if isinstance(rt.table_json, list) else json.loads(rt.table_json)
        print("文件:", row.raw_file.filename)
        print("前 10 行（每行前 15 列）:")
        for i, r in enumerate(data[:10]):
            part = list(r[:15]) if len(r) >= 15 else list(r)
            print(f"  行{i}: {part}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
