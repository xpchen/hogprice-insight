"""
将包含「月度-淘汰母猪屠宰厂宰杀量」或「淘汰母猪屠宰」的 Excel 文件导入到 raw 层（raw_file + raw_sheet + raw_table），
供 E2 淘汰母猪屠宰环比使用。

用法:
  python backend/scripts/import_cull_slaughter_sheets.py [路径1.xlsx] [路径2.xlsx] ...
  无参数时自动扫描 docs/生猪 下包含目标 sheet 的 xlsx 并导入。
  - 涌益 sheet「月度-淘汰母猪屠宰厂宰杀量」：来自涌益咨询周度数据等 xlsx
  - 钢联 sheet「淘汰母猪屠宰」：来自钢联自动更新模板等 xlsx（若需 2025 年数据，请用含 2025 的 Excel 重新导入）

若某文件已按相同内容导入过（相同 file_hash），会先删除旧记录再重新导入。
API 按 sheet 名取数时会使用「最新一次导入」的版本，故更新 2025 数据后重新运行本脚本即可。
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import hashlib

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TARGET_SHEETS = {"月度-淘汰母猪屠宰厂宰杀量", "淘汰母猪屠宰"}


def workbook_has_target_sheet(path: Path) -> bool:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        has = bool(TARGET_SHEETS & set(wb.sheetnames))
        wb.close()
        return has
    except Exception:
        return False


def import_excel_to_raw(db, excel_path: Path, max_rows: int = 2000):
    """将 Excel 全部 sheet 导入 raw_file / raw_sheet / raw_table（与 import_industry_data 一致）。"""
    from app.models.import_batch import ImportBatch
    from app.models.raw_file import RawFile
    from app.models.raw_sheet import RawSheet
    from app.models.raw_table import RawTable
    from app.services.ingestors.raw_writer import save_raw_file, save_all_sheets_from_workbook

    with open(excel_path, "rb") as f:
        file_content = f.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    filename = excel_path.name

    existing = db.query(RawFile).filter(RawFile.file_hash == file_hash).first()
    if existing:
        print(f"  文件已存在（相同 hash），删除旧数据后重新导入: {existing.filename}")
        for old_sheet in db.query(RawSheet).filter(RawSheet.raw_file_id == existing.id).all():
            old_table = db.query(RawTable).filter(RawTable.raw_sheet_id == old_sheet.id).first()
            if old_table:
                db.delete(old_table)
            db.delete(old_sheet)
        db.delete(existing)
        db.flush()

    batch = ImportBatch(
        filename=filename,
        file_hash=file_hash,
        uploader_id=1,
        status="completed",
        source_code="CULL_SLAUGHTER_RAW",
        total_rows=0,
        success_rows=0,
        failed_rows=0,
    )
    db.add(batch)
    db.flush()

    raw_file = save_raw_file(db=db, batch_id=batch.id, filename=filename, file_content=file_content)
    raw_sheets = save_all_sheets_from_workbook(
        db=db,
        raw_file_id=raw_file.id,
        workbook_or_path=str(excel_path),
        sparse=False,
        max_rows=max_rows,
    )
    return raw_sheets


def main():
    from app.core.database import SessionLocal

    paths = []
    if len(sys.argv) >= 2:
        for p in sys.argv[1:]:
            path = Path(p)
            if not path.is_absolute():
                path = (script_dir.parent / path).resolve()
            if not path.exists():
                print(f"跳过（不存在）: {path}")
                continue
            if path.suffix.lower() != ".xlsx":
                print(f"跳过（非 xlsx）: {path}")
                continue
            if workbook_has_target_sheet(path):
                paths.append(path)
            else:
                print(f"跳过（不包含目标 sheet）: {path}")
    else:
        # 无参数时自动扫描 docs/生猪 下包含目标 sheet 的 xlsx
        search_dir = script_dir.parent / "docs" / "生猪"
        if search_dir.exists():
            for path in sorted(search_dir.glob("*.xlsx")):
                if workbook_has_target_sheet(path):
                    paths.append(path)
                    print(f"找到可导入: {path.name}")
        if not paths:
            print("用法: python import_cull_slaughter_sheets.py [路径1.xlsx] [路径2.xlsx] ...")
            print("  无参数时将扫描 docs/生猪 下包含目标 sheet 的 xlsx")
            print("  涌益 sheet「月度-淘汰母猪屠宰厂宰杀量」来自涌益周度数据 xlsx")
            print("  钢联 sheet「淘汰母猪屠宰」来自钢联模板 xlsx")
            sys.exit(1)

    if not paths:
        print("没有找到包含「月度-淘汰母猪屠宰厂宰杀量」或「淘汰母猪屠宰」的 xlsx 文件。")
        sys.exit(1)

    db = SessionLocal()
    try:
        for excel_path in paths:
            print(f"\n导入: {excel_path}")
            raw_sheets = import_excel_to_raw(db, excel_path)
            print(f"  已导入 {len(raw_sheets)} 个 sheet")
            for s in raw_sheets:
                if s.sheet_name in TARGET_SHEETS:
                    print(f"    ✓ {s.sheet_name}")
        db.commit()
        print("\n导入完成。")
    except Exception as e:
        db.rollback()
        print(f"\n导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
