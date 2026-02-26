"""0226 目录 8 个 Excel 全量入库脚本

导入 docs/0226/生猪/ 下的 8 个文件（排除 4、生猪基差和月间价差研究.xlsx）：
1. 4.1、生猪期货升贴水数据（盘面结算价）.xlsx - PREMIUM_DATA
2. 2、【生猪产业数据】.xlsx - INDUSTRY_DATA
3. 1、价格：钢联自动更新模板.xlsx - GANGLIAN_DAILY
4. 3.1、集团企业出栏跟踪【分省区】.xlsx - ENTERPRISE_DAILY
5. 3.2、集团企业月度数据跟踪.xlsx - ENTERPRISE_MONTHLY
6. 3.3、白条市场跟踪.xlsx - WHITE_STRIP_MARKET
7. 涌益咨询日度数据.xlsx - YONGYI_DAILY
8. 涌益咨询 周度数据.xlsx - YONGYI_WEEKLY
"""
import sys
import os
import io
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.sys_user import SysUser
from app.models.import_batch import ImportBatch
from app.services.ingest_service import _run_single_import


def get_or_create_user(db):
    """获取或创建导入用户"""
    user = db.query(SysUser).filter(SysUser.username == "admin").first()
    if not user:
        from app.core.security import get_password_hash
        user = SysUser(
            username="admin",
            password_hash=get_password_hash("admin123"),
            display_name="管理员",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"  ✓ 创建用户: {user.username} (ID: {user.id})")
    else:
        print(f"  ✓ 使用用户: {user.username} (ID: {user.id})")
    return user


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    base_dir = project_root / "docs" / "0226" / "生猪"
    yongyi_dir = base_dir / "涌益生猪项目数据库"

    files_to_import = [
        (base_dir / "4.1、生猪期货升贴水数据（盘面结算价）.xlsx", "4.1、生猪期货升贴水数据（盘面结算价）.xlsx"),
        (base_dir / "2、【生猪产业数据】.xlsx", "2、【生猪产业数据】.xlsx"),
        (base_dir / "1、价格：钢联自动更新模板.xlsx", "1、价格：钢联自动更新模板.xlsx"),
        (base_dir / "3.1、集团企业出栏跟踪【分省区】.xlsx", "3.1、集团企业出栏跟踪【分省区】.xlsx"),
        (base_dir / "3.2、集团企业月度数据跟踪.xlsx", "3.2、集团企业月度数据跟踪.xlsx"),
        (base_dir / "3.3、白条市场跟踪.xlsx", "3.3、白条市场跟踪.xlsx"),
        (yongyi_dir / "涌益咨询日度数据.xlsx", "涌益咨询日度数据.xlsx"),
        (yongyi_dir / "涌益咨询 周度数据.xlsx", "涌益咨询 周度数据.xlsx"),
    ]

    print("=" * 60)
    print("0226 目录 8 个 Excel 全量入库")
    print("=" * 60)

    db = SessionLocal()
    results = []

    try:
        print("\n1. 准备用户...")
        user = get_or_create_user(db)

        print("\n2. 开始导入...")
        for i, (file_path, filename) in enumerate(files_to_import, 1):
            print(f"\n[{i}/{len(files_to_import)}] {filename}")
            if not file_path.exists():
                print(f"  ✗ 文件不存在: {file_path}")
                results.append({"file": filename, "success": False, "error": "文件不存在"})
                continue

            try:
                file_content = file_path.read_bytes()
                result = _run_single_import(
                    db=db,
                    file_content=file_content,
                    filename=filename,
                    uploader_id=user.id,
                    template_type=None,
                )
                err_cnt = result.get("errors", [])
                if isinstance(err_cnt, (list, tuple)):
                    err_cnt = len(err_cnt)
                success = result.get("success", False)
                status = "✓" if success else "⚠"
                print(f"  {status} 成功: {result.get('inserted', 0)} 新增, "
                      f"{result.get('updated', 0)} 更新, {err_cnt} 错误")
                results.append({
                    "file": filename,
                    "success": success,
                    "inserted": result.get("inserted", 0),
                    "updated": result.get("updated", 0),
                    "errors": err_cnt,
                })
            except Exception as e:
                print(f"  ✗ 导入失败: {e}")
                results.append({"file": filename, "success": False, "error": str(e)})

        # 汇总
        print("\n" + "=" * 60)
        print("导入汇总")
        print("=" * 60)
        success_count = sum(1 for r in results if r.get("success"))
        total_inserted = sum(r.get("inserted", 0) for r in results)
        total_updated = sum(r.get("updated", 0) for r in results)
        print(f"\n成功: {success_count}/{len(results)}")
        print(f"总新增: {total_inserted}, 总更新: {total_updated}")
        for r in results:
            s = "✓" if r.get("success") else "✗"
            print(f"  {s} {r['file']}")
        if success_count == len(results):
            print("\n全部导入完成。")
        else:
            print(f"\n有 {len(results) - success_count} 个文件失败。")

        # 刷新快速图表缓存
        if success_count > 0:
            try:
                from app.services.quick_chart_service import regenerate_cache_sync
                print("\n刷新快速图表缓存...")
                regenerate_cache_sync(db)
                print("  ✓ 缓存已刷新")
            except Exception as ex:
                print(f"  ⚠ 缓存刷新失败: {ex}")

    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
