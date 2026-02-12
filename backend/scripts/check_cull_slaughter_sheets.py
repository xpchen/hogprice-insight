"""
检查「淘汰母猪屠宰」相关两个 sheet 是否在数据库中，并可在指定目录下查找包含它们的 Excel 文件。

目标 sheet：
- 涌益：月度-淘汰母猪屠宰厂宰杀量
- 钢联：淘汰母猪屠宰
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TARGET_SHEETS = {
    "涌益": "月度-淘汰母猪屠宰厂宰杀量",
    "钢联": "淘汰母猪屠宰",
}


def check_db():
    """检查数据库中是否存在这两个 sheet，以及所属文件名。"""
    from app.core.database import SessionLocal
    from app.models.raw_sheet import RawSheet
    from app.models.raw_table import RawTable
    from app.models.raw_file import RawFile

    db = SessionLocal()
    try:
        print("=" * 60)
        print("1. 数据库中的 sheet 检查")
        print("=" * 60)
        for source, sheet_name in TARGET_SHEETS.items():
            row = (
                db.query(RawSheet)
                .join(RawFile, RawSheet.raw_file_id == RawFile.id)
                .filter(RawSheet.sheet_name == sheet_name)
                .first()
            )
            if row:
                rt = db.query(RawTable).filter(RawTable.raw_sheet_id == row.id).first()
                has_data = "有" if (rt and rt.table_json) else "无"
                print(f"  [{source}] {sheet_name}")
                print(f"      文件: {row.raw_file.filename}")
                print(f"      raw_table: {has_data} 数据")
            else:
                print(f"  [{source}] {sheet_name}")
                print(f"      未找到（需要导入）")
        return
    finally:
        db.close()


def find_excel_with_sheets(search_dir: Path):
    """在指定目录下查找包含目标 sheet 的 .xlsx 文件（不递归）。"""
    try:
        import openpyxl
    except ImportError:
        print("未安装 openpyxl，跳过本地文件扫描。")
        return
    if not search_dir.exists():
        print(f"目录不存在: {search_dir}")
        return
    print()
    print("  目录:", search_dir)
    xlsx_files = list(search_dir.glob("*.xlsx"))
    if not xlsx_files:
        print(f"  目录下无 .xlsx 文件: {search_dir}")
        return
    found = {name: [] for name in TARGET_SHEETS.values()}
    for path in sorted(xlsx_files):
        try:
            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            names = set(wb.sheetnames)
            wb.close()
        except Exception as e:
            print(f"  跳过 {path.name}: {e}")
            continue
        for source, sheet_name in TARGET_SHEETS.items():
            if sheet_name in names:
                found[sheet_name].append(str(path))
    for sheet_name in TARGET_SHEETS.values():
        paths = found[sheet_name]
        if paths:
            print(f"  「{sheet_name}」 存在于:")
            for p in paths:
                print(f"    - {p}")
        else:
            print(f"  「{sheet_name}」 未在任何 .xlsx 中找到。")


def main():
    check_db()
    repo = script_dir.parent
    search_dirs = [repo / "docs" / "生猪"]
    if len(sys.argv) > 1:
        search_dirs.extend(Path(p) for p in sys.argv[1:])
    print()
    print("=" * 60)
    print("2. 在本地目录中查找包含目标 sheet 的 Excel 文件")
    print("=" * 60)
    for d in search_dirs:
        find_excel_with_sheets(d)
    print()
    print("若 sheet 未在库中，请将对应 Excel 放入 docs/生猪 后运行:")
    print("  python backend/scripts/import_cull_slaughter_sheets.py <涌益周度.xlsx> [钢联模板.xlsx]")
    print("或通过「数据导入」上传涌益周度/钢联模板并选择对应模板类型。")


if __name__ == "__main__":
    main()
