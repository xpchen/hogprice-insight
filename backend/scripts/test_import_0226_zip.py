"""测试 docs/0226.zip 导入"""
import sys
import io
from pathlib import Path

script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import zipfile

repo = script_dir.parent.parent  # project root
zip_path = repo / "docs" / "0226.zip"


def main():
    from app.core.database import SessionLocal
    from app.models.sys_user import SysUser
    from app.services.ingest_template_detector import detect_template
    from app.services.ingestors.unified_ingestor import unified_import

    db = SessionLocal()
    try:
        user = db.query(SysUser).filter(SysUser.username == "admin").first()
        if not user:
            print("请先创建 admin 用户")
            return 1

        if not zip_path.exists():
            print(f"zip 不存在: {zip_path}")
            return 1

        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                if not name.lower().endswith((".xlsx", ".xls")):
                    continue
                base_name = name.split("/")[-1].split("\\")[-1]
                content = z.read(name)
                print(f"\n导入: {base_name}")

                try:
                    template_type = detect_template(content, base_name)
                    print(f"  模板: {template_type}")

                    if template_type == "GANGLIAN_DAILY":
                        result = unified_import(
                            db=db,
                            file_content=content,
                            filename=base_name,
                            uploader_id=user.id,
                            dataset_type="GANGLIAN_DAILY",
                            source_code="GANGLIAN",
                        )
                    elif template_type == "YONGYI_DAILY":
                        result = unified_import(
                            db=db,
                            file_content=content,
                            filename=base_name,
                            uploader_id=user.id,
                            dataset_type="YONGYI_DAILY",
                            source_code="YONGYI",
                        )
                    elif template_type == "YONGYI_WEEKLY":
                        result = unified_import(
                            db=db,
                            file_content=content,
                            filename=base_name,
                            uploader_id=user.id,
                            dataset_type="YONGYI_WEEKLY",
                            source_code="YONGYI",
                        )
                    else:
                        print(f"  跳过（未实现）: {template_type}")
                        continue

                    print(f"  结果: success={result.get('success')}, inserted={result.get('inserted')}, "
                          f"updated={result.get('updated')}, errors={result.get('errors')}")

                except Exception as e:
                    print(f"  错误: {e}")
                    import traceback
                    traceback.print_exc()

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
