"""查看导入错误"""
import sys
import os
import io

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.ingest_error import IngestError
from app.models.import_batch import ImportBatch
from collections import Counter

db = SessionLocal()

try:
    # 获取最近的批次
    batches = db.query(ImportBatch).order_by(ImportBatch.id.desc()).limit(5).all()
    
    print("="*60)
    print("Import Errors Analysis")
    print("="*60)
    
    for batch in batches:
        print(f"\nBatch ID: {batch.id}")
        print(f"File: {batch.filename}")
        print(f"Status: {batch.status}")
        print(f"Success: {batch.success_rows}, Failed: {batch.failed_rows}")
        
        errors = db.query(IngestError).filter(IngestError.batch_id == batch.id).all()
        print(f"Total errors: {len(errors)}")
        
        if errors:
            # 按sheet分组
            sheet_errors = Counter([e.sheet_name for e in errors if e.sheet_name])
            print(f"\nErrors by sheet:")
            for sheet, count in sheet_errors.most_common():
                print(f"  {sheet}: {count}")
            
            # 按错误类型分组
            type_errors = Counter([e.error_type for e in errors if e.error_type])
            print(f"\nErrors by type:")
            for err_type, count in type_errors.most_common():
                print(f"  {err_type}: {count}")
            
            # 显示前10个错误详情
            print(f"\nFirst 10 errors:")
            for i, error in enumerate(errors[:10], 1):
                print(f"  {i}. Sheet: {error.sheet_name or 'N/A'}, Type: {error.error_type}, Row: {error.row_no}, Msg: {error.message[:80]}")
        
        print("-"*60)
        
finally:
    db.close()
