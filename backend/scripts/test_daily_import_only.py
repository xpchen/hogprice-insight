"""专门测试涌益日度数据导入（优化存储后）"""
import sys
import os
import io
from pathlib import Path
from datetime import datetime

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.sys_user import SysUser
from app.services.ingest_template_detector import detect_template
from app.services.ingestors.unified_ingestor import unified_import


def get_or_create_test_user(db):
    """获取或创建测试用户"""
    user = db.query(SysUser).filter(SysUser.username == "admin").first()
    if not user:
        from app.core.security import get_password_hash
        user = SysUser(
            username="test_admin",
            password_hash=get_password_hash("test123456"),
            display_name="测试管理员",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"  [OK] Created test user: {user.username} (ID: {user.id})")
    else:
        print(f"  [OK] Using existing user: {user.username} (ID: {user.id})")
    return user


def import_daily_file(db, file_path: Path, uploader_id: int):
    """导入日度文件"""
    filename = file_path.name
    print(f"\n{'='*60}")
    print(f"Processing file: {filename}")
    print(f"{'='*60}")
    
    if not file_path.exists():
        print(f"  [ERROR] File not found: {file_path}")
        return {
            "success": False,
            "error": f"File not found: {file_path}"
        }
    
    # 读取文件内容
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
        print(f"  [OK] File size: {len(file_content) / 1024:.2f} KB")
    except Exception as e:
        print(f"  [ERROR] Failed to read file: {e}")
        return {
            "success": False,
            "error": f"Failed to read file: {e}"
        }
    
    # 检测模板类型
    try:
        template_type = detect_template(file_content, filename)
        print(f"  [OK] Detected template type: {template_type}")
    except Exception as e:
        print(f"  [ERROR] Template detection failed: {e}")
        return {
            "success": False,
            "error": f"Template detection failed: {e}"
        }
    
    # 导入数据
    start_time = datetime.now()
    result = None
    
    try:
        print("  -> Using unified import workflow (YONGYI_DAILY)...")
        result = unified_import(
            db=db,
            file_content=file_content,
            filename=filename,
            uploader_id=uploader_id,
            dataset_type="YONGYI_DAILY",
            source_code="YONGYI"
        )
        
        # 显示结果
        duration = (datetime.now() - start_time).total_seconds()
        if result.get("success"):
            inserted = result.get("inserted", 0)
            updated = result.get("updated", 0)
            errors = result.get("errors", 0)
            if isinstance(errors, list):
                errors = len(errors)
            
            print(f"\n  [OK] Import successful!")
            print(f"     - Inserted: {inserted} records")
            print(f"     - Updated: {updated} records")
            print(f"     - Errors: {errors} records")
            print(f"     - Duration: {duration:.2f} seconds")
            
            if result.get("total_sheets"):
                print(f"     - Total sheets: {result.get('total_sheets')}")
            if result.get("parsed_sheets"):
                print(f"     - Parsed sheets: {result.get('parsed_sheets')}")
            
            return {
                "success": True,
                "inserted": inserted,
                "updated": updated,
                "errors": errors,
                "duration": duration,
                "batch_id": result.get("batch_id")
            }
        else:
            error_msg = result.get("error") or str(result.get("errors", []))
            print(f"\n  [ERROR] Import failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "duration": duration
            }
            
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"\n  [ERROR] Import exception: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": error_msg,
            "duration": (datetime.now() - start_time).total_seconds()
        }


def verify_import_results(db, batch_id):
    """验证导入结果"""
    print(f"\n{'='*60}")
    print("Verifying Import Results")
    print(f"{'='*60}")
    
    # 检查批次
    from app.models.import_batch import ImportBatch
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch:
        status_icon = "OK" if batch.status == "success" else "WARN" if batch.status == "partial" else "ERROR"
        print(f"\nBatch ID: {batch.id}")
        print(f"Status: {batch.status}")
        print(f"Success: {batch.success_rows}, Failed: {batch.failed_rows}")
        print(f"Inserted: {batch.inserted_count}, Updated: {batch.updated_count}")
        print(f"Sheets: {batch.sheet_count}")
    
    # 检查raw_table存储情况
    try:
        from app.models.raw_sheet import RawSheet
        from app.models.raw_table import RawTable
        
        raw_sheets = db.query(RawSheet).join(ImportBatch).filter(ImportBatch.id == batch_id).all()
        print(f"\nRaw sheets: {len(raw_sheets)}")
        
        raw_tables = db.query(RawTable).join(RawSheet).join(ImportBatch).filter(ImportBatch.id == batch_id).all()
        print(f"Raw tables stored: {len(raw_tables)}")
        
        if len(raw_tables) < len(raw_sheets):
            skipped = len(raw_sheets) - len(raw_tables)
            print(f"  [INFO] {skipped} sheets skipped raw_table storage (too large)")
    except Exception as e:
        print(f"  [WARN] Could not check raw tables: {e}")
    
    # 检查fact_observation数据量
    try:
        from app.models.fact_observation import FactObservation
        obs_count = db.query(FactObservation).join(ImportBatch).filter(ImportBatch.id == batch_id).count()
        print(f"\nfact_observation records (this batch): {obs_count}")
        
        total_obs_count = db.query(FactObservation).count()
        print(f"fact_observation total records: {total_obs_count}")
    except Exception as e:
        print(f"  [WARN] Could not check fact_observation: {e}")


def main():
    """主函数"""
    print("="*60)
    print("Yongyi Daily Data Import Test (Optimized Storage)")
    print("="*60)
    
    # 确定文件路径
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    docs_dir = project_root / "docs"
    
    file_path = docs_dir / "2026年2月2日涌益咨询日度数据.xlsx"
    
    db = SessionLocal()
    
    try:
        # 1. 获取或创建测试用户
        print("\n1. Preparing test user...")
        user = get_or_create_test_user(db)
        
        # 2. 导入文件
        print("\n2. Starting import...")
        result = import_daily_file(db, file_path, user.id)
        
        # 3. 验证导入结果
        if result.get("success") and result.get("batch_id"):
            verify_import_results(db, result["batch_id"])
        
        # 4. 汇总
        print(f"\n{'='*60}")
        print("Import Summary")
        print(f"{'='*60}")
        
        if result.get("success"):
            print(f"\n[OK] Import successful!")
            print(f"Inserted: {result.get('inserted', 0)}")
            print(f"Updated: {result.get('updated', 0)}")
            print(f"Errors: {result.get('errors', 0)}")
            print(f"Duration: {result.get('duration', 0):.2f} seconds")
        else:
            print(f"\n[ERROR] Import failed: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
