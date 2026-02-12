# -*- coding: utf-8 -*-
"""
使用 WHITE_STRIP_MARKET_V1 配置重新导入「3.3、白条市场跟踪.xlsx」
"""
import sys
import io
from pathlib import Path

script_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(script_dir))
if sys.stdout.encoding and sys.stdout.encoding.upper() != 'UTF-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.ingestors.unified_ingestor import unified_import
from app.services.ingestors.profile_loader import load_profile_from_json, get_profile_by_code
from app.models.dim_source import DimSource


def main():
    project_root = script_dir.parent
    candidates = [
        project_root / "docs" / "生猪" / "3.3、白条市场跟踪.xlsx",
        project_root / "docs" / "3.3、白条市场跟踪.xlsx",
    ]
    file_path = None
    for p in candidates:
        if p.exists():
            file_path = p
            break
    if not file_path:
        print("未找到文件 3.3、白条市场跟踪.xlsx")
        print("请将文件放在以下任一位置后重试：")
        for p in candidates:
            print(f"  - {p}")
        return 1

    profile_path = project_root / "docs" / "ingest_profile_white_strip_market_v1.json"
    if not profile_path.exists():
        print(f"Profile 不存在: {profile_path}")
        return 1

    print(f"文件: {file_path}")
    print(f"Profile: {profile_path.name} (WHITE_STRIP_MARKET_V1)")

    with open(file_path, "rb") as f:
        file_content = f.read()

    db: Session = SessionLocal()
    try:
        # 确保数据源存在
        source = db.query(DimSource).filter(DimSource.source_code == "WHITE_STRIP_MARKET").first()
        if not source:
            source = DimSource(
                source_code="WHITE_STRIP_MARKET",
                source_name="白条市场跟踪",
                source_type="WHITE_STRIP_MARKET",
            )
            db.add(source)
            db.commit()
            print("已创建数据源: WHITE_STRIP_MARKET")

        # 加载 profile（若尚未入库）
        try:
            profile = load_profile_from_json(db, str(profile_path))
            print(f"已加载 Profile: {profile.profile_code} ({len(profile.sheets)} sheets)")
        except Exception as e:
            profile = get_profile_by_code(db, "WHITE_STRIP_MARKET_V1")
            if not profile:
                print(f"Profile 加载失败: {e}")
                return 1
            print(f"使用已有 Profile: {profile.profile_code}")

        result = unified_import(
            db=db,
            file_content=file_content,
            filename=file_path.name,
            uploader_id=1,
            dataset_type=profile.dataset_type,
            source_code=profile.source_code,
        )

        print("\n导入结果:")
        print(f"  成功: {result.get('success', False)}")
        if result.get("success"):
            print(f"  插入: {result.get('inserted', 0)} 条")
            print(f"  更新: {result.get('updated', 0)} 条")
            errs = result.get("errors")
            if errs and isinstance(errs, list):
                print(f"  错误/警告: {len(errs)} 个")
                for e in errs[:10]:
                    print(f"    - {e}")
            elif errs:
                print(f"  错误/警告: {errs}")
        else:
            print(f"  错误: {result.get('errors', '未知错误')}")
        return 0 if result.get("success") else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
