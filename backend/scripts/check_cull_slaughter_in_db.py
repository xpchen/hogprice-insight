"""
查询数据库中「淘汰母猪屠宰」相关 raw 数据：来自哪个文件、多少行、日期范围。
"""
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


def parse_date_cell(cell):
    """从单元格解析出年月字符串"""
    if cell is None:
        return None
    if hasattr(cell, 'strftime'):
        return cell.strftime("%Y-%m")
    s = str(cell).strip()
    if not s or s == '指标名称' or s == '单位' or s == '更新时间' or s == '钢联数据':
        return None
    if len(s) >= 7 and s[4] == '-':
        return s[:7]  # YYYY-MM
    if 'T' in s and s[4] == '-':
        return s[:7]
    return None


def main():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("1. 所有包含 sheet「淘汰母猪屠宰」的 raw_file")
        print("=" * 70)

        sheets = (
            db.query(RawSheet)
            .join(RawFile)
            .filter(RawSheet.sheet_name == "淘汰母猪屠宰")
            .order_by(RawFile.id.asc())
            .all()
        )

        if not sheets:
            print("  未找到任何 sheet 名为「淘汰母猪屠宰」的记录。")
            return

        for i, sh in enumerate(sheets):
            rf = sh.raw_file
            rt = db.query(RawTable).filter(RawTable.raw_sheet_id == sh.id).first()
            row_count = 0
            date_min = date_max = None
            sample_dates = []
            if rt and rt.table_json:
                data = rt.table_json if isinstance(rt.table_json, list) else json.loads(rt.table_json)
                row_count = len(data)
                # 钢联表：第4行起 col0=日期
                for r in data[4:]:
                    if len(r) < 1:
                        continue
                    ym = parse_date_cell(r[0])
                    if ym:
                        sample_dates.append(ym)
                if sample_dates:
                    date_min = min(sample_dates)
                    date_max = max(sample_dates)

            print(f"\n  [{i+1}] raw_file.id = {rf.id}")
            print(f"      文件名: {rf.filename}")
            print(f"      created_at: {rf.created_at}")
            print(f"      raw_sheet.id = {sh.id}, 表行数 = {row_count}")
            print(f"      日期范围: {date_min} ~ {date_max}")
            if sample_dates:
                print(f"      前5个月: {sample_dates[:5]}")
                print(f"      后5个月: {sample_dates[-5:]}")

        print("\n" + "=" * 70)
        print("2. API 会取哪一条？（按 RawFile.id 降序取第一条）")
        print("=" * 70)

        latest = (
            db.query(RawSheet)
            .join(RawFile)
            .filter(RawSheet.sheet_name == "淘汰母猪屠宰")
            .order_by(RawFile.id.desc())
            .first()
        )
        if latest:
            rf = latest.raw_file
            rt = db.query(RawTable).filter(RawTable.raw_sheet_id == latest.id).first()
            print(f"   当前会使用: raw_file.id = {rf.id}, 文件名 = {rf.filename}")
            if rt and rt.table_json:
                data = rt.table_json if isinstance(rt.table_json, list) else json.loads(rt.table_json)
                print(f"   表行数: {len(data)}")
                if len(data) > 4:
                    print(f"   第4行(首行数据): {data[4][:5]}")
                    print(f"   最后一行: {data[-1][:5]}")
        else:
            print("   无记录")

        print("\n" + "=" * 70)
        print("3. 月度-淘汰母猪屠宰厂宰杀量（涌益）")
        print("=" * 70)

        yongyi = (
            db.query(RawSheet)
            .join(RawFile)
            .filter(RawSheet.sheet_name == "月度-淘汰母猪屠宰厂宰杀量")
            .order_by(RawFile.id.desc())
            .first()
        )
        if yongyi:
            rf = yongyi.raw_file
            rt = db.query(RawTable).filter(RawTable.raw_sheet_id == yongyi.id).first()
            print(f"   使用: {rf.filename}, raw_file.id = {rf.id}")
            if rt and rt.table_json:
                data = rt.table_json if isinstance(rt.table_json, list) else json.loads(rt.table_json)
                print(f"   表行数: {len(data)}")
                dates = []
                for r in data[2:]:
                    if len(r) < 1:
                        continue
                    ym = parse_date_cell(r[0])
                    if ym:
                        dates.append(ym)
                if dates:
                    print(f"   日期范围: {min(dates)} ~ {max(dates)}")
        else:
            print("   未找到")

    finally:
        db.close()


if __name__ == "__main__":
    main()
