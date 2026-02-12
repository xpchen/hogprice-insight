"""
导入【生猪产业数据】.xlsx文件
用于E2. 多渠道汇总数据
直接导入到raw_table，不进行解析
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.models.import_batch import ImportBatch
from app.models.raw_file import RawFile
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.services.ingestors.raw_writer import save_raw_file, save_all_sheets_from_workbook

def import_industry_data():
    """导入生猪产业数据文件"""
    excel_path = Path(script_dir.parent) / "docs" / "生猪" / "2、【生猪产业数据】.xlsx"
    
    if not excel_path.exists():
        print(f"文件不存在: {excel_path}")
        return
    
    print("=" * 80)
    print("导入【生猪产业数据】.xlsx")
    print("=" * 80)
    
    # 读取文件内容
    with open(excel_path, 'rb') as f:
        file_content = f.read()
    
    db: Session = SessionLocal()
    try:
        # 1. 创建import_batch
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # 检查是否已导入，如果存在则删除旧数据
        existing_file = db.query(RawFile).filter(RawFile.file_hash == file_hash).first()
        if existing_file:
            print(f"\n文件已存在，删除旧数据后重新导入")
            print(f"  文件ID: {existing_file.id}")
            print(f"  文件名: {existing_file.filename}")
            print(f"  导入时间: {existing_file.created_at}")
            
            # 删除旧的sheet和table数据
            from app.models.raw_sheet import RawSheet as RS
            from app.models.raw_table import RawTable as RT
            
            old_sheets = db.query(RS).filter(RS.raw_file_id == existing_file.id).all()
            for old_sheet in old_sheets:
                old_table = db.query(RT).filter(RT.raw_sheet_id == old_sheet.id).first()
                if old_table:
                    db.delete(old_table)
                db.delete(old_sheet)
            db.delete(existing_file)
            db.flush()
            print(f"  已删除旧数据")
        
        batch = ImportBatch(
            filename=excel_path.name,
            file_hash=file_hash,
            uploader_id=1,  # 假设admin用户ID为1
            status="completed",
            source_code="INDUSTRY_DATA",
            total_rows=0,
            success_rows=0,
            failed_rows=0
        )
        db.add(batch)
        db.flush()
        batch_id = batch.id
        
        # 2. 保存raw_file
        raw_file = save_raw_file(
            db=db,
            batch_id=batch_id,
            filename=excel_path.name,
            file_content=file_content
        )
        
        # 3. 保存所有sheet到raw_table
        print(f"\n开始导入sheet...")
        # 重新导入，确保存储完整数据
        # 先删除旧的sheet数据
        old_sheets = db.query(RawSheet).filter(RawSheet.raw_file_id == raw_file.id).all()
        for old_sheet in old_sheets:
            old_table = db.query(RawTable).filter(RawTable.raw_sheet_id == old_sheet.id).first()
            if old_table:
                db.delete(old_table)
            db.delete(old_sheet)
        db.flush()
        
        # 重新导入所有sheet，使用更大的max_rows限制
        raw_sheets = save_all_sheets_from_workbook(
            db=db,
            raw_file_id=raw_file.id,
            workbook_or_path=str(excel_path),
            sparse=False,  # 不使用稀疏格式，保留完整数据
            max_rows=200  # 增加到200行，应该足够覆盖所有数据
        )
        
        print(f"\n导入结果:")
        print(f"  总sheet数: {len(raw_sheets)}")
        print(f"\n已导入的sheet:")
        from app.models.raw_table import RawTable as RT
        for sheet in raw_sheets:
            raw_table = db.query(RT).filter(RT.raw_sheet_id == sheet.id).first()
            table_size = "有数据" if raw_table else "无数据"
            print(f"  - {sheet.sheet_name} ({table_size})")
        
        db.commit()
        print("\n✓ 导入完成")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import_industry_data()
