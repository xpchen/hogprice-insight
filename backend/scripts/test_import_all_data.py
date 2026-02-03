"""五类数据全量入库自测脚本

自动导入以下五类数据：
1. 钢联自动更新模板.xlsx - GANGLIAN_DAILY
2. 2026年2月2日涌益咨询日度数据.xlsx - YONGYI_DAILY
3. lh_ftr.xlsx - LH_FTR
4. lh_opt.xlsx - LH_OPT
5. 2026.1.16-2026.1.22涌益咨询 周度数据.xlsx - YONGYI_WEEKLY
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

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.sys_user import SysUser
from app.models.import_batch import ImportBatch
from app.services.ingest_template_detector import detect_template
from app.services.ingestors import import_lh_ftr, import_lh_opt
from app.services.ingestors.unified_ingestor import unified_import


def get_or_create_test_user(db):
    """获取或创建测试用户"""
    # 优先使用admin用户
    user = db.query(SysUser).filter(SysUser.username == "admin").first()
    if not user:
        # 如果没有admin，创建test_admin
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
        print(f"  ✓ 创建测试用户: {user.username} (ID: {user.id})")
    else:
        print(f"  ✓ 使用现有用户: {user.username} (ID: {user.id})")
    return user


def create_batch_for_legacy_import(db, filename, source_code, uploader_id):
    """为旧导入器创建批次"""
    batch = ImportBatch(
        filename=filename,
        file_hash="",  # 旧导入器可能不需要hash
        uploader_id=uploader_id,
        status="processing",
        source_code=source_code,
        total_rows=0,
        success_rows=0,
        failed_rows=0
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch.id


def import_file(db, file_path: Path, uploader_id: int):
    """导入单个文件"""
    filename = file_path.name
    print(f"\n{'='*60}")
    print(f"处理文件: {filename}")
    print(f"{'='*60}")
    
    if not file_path.exists():
        print(f"  ✗ 文件不存在: {file_path}")
        return {
            "success": False,
            "error": f"文件不存在: {file_path}"
        }
    
    # 读取文件内容
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
        print(f"  ✓ 文件大小: {len(file_content) / 1024:.2f} KB")
    except Exception as e:
        print(f"  ✗ 读取文件失败: {e}")
        return {
            "success": False,
            "error": f"读取文件失败: {e}"
        }
    
    # 检测模板类型
    try:
        template_type = detect_template(file_content, filename)
        print(f"  ✓ 检测到模板类型: {template_type}")
    except Exception as e:
        print(f"  ✗ 模板检测失败: {e}")
        return {
            "success": False,
            "error": f"模板检测失败: {e}"
        }
    
    # 根据模板类型选择导入方式
    start_time = datetime.now()
    result = None
    
    try:
        if template_type == "LH_FTR":
            print("  → 使用期货导入器...")
            batch_id = create_batch_for_legacy_import(db, filename, "DCE", uploader_id)
            result = import_lh_ftr(db, file_content, batch_id)
            
        elif template_type == "LH_OPT":
            print("  → 使用期权导入器...")
            batch_id = create_batch_for_legacy_import(db, filename, "DCE", uploader_id)
            result = import_lh_opt(db, file_content, batch_id)
            
        elif template_type == "YONGYI_DAILY":
            print("  → 使用统一导入工作流 (YONGYI_DAILY)...")
            result = unified_import(
                db=db,
                file_content=file_content,
                filename=filename,
                uploader_id=uploader_id,
                dataset_type="YONGYI_DAILY",
                source_code="YONGYI"
            )
            
        elif template_type == "YONGYI_WEEKLY":
            print("  → 使用统一导入工作流 (YONGYI_WEEKLY)...")
            result = unified_import(
                db=db,
                file_content=file_content,
                filename=filename,
                uploader_id=uploader_id,
                dataset_type="YONGYI_WEEKLY",
                source_code="YONGYI"
            )
            
        elif template_type == "GANGLIAN_DAILY":
            print("  → 使用钢联导入器...")
            from app.services.ingestors import import_ganglian_daily
            batch_id = create_batch_for_legacy_import(db, filename, "MYSTEEL", uploader_id)
            result = import_ganglian_daily(db, file_content, batch_id)
            
        else:
            print(f"  ✗ 不支持的模板类型: {template_type}")
            return {
                "success": False,
                "error": f"不支持的模板类型: {template_type}"
            }
        
        # 显示结果
        duration = (datetime.now() - start_time).total_seconds()
        if result.get("success"):
            inserted = result.get("inserted", 0)
            updated = result.get("updated", 0)
            errors = result.get("errors", 0)
            if isinstance(errors, list):
                errors = len(errors)
            
            print(f"\n  ✓ 导入成功！")
            print(f"     - 新增: {inserted} 条")
            print(f"     - 更新: {updated} 条")
            print(f"     - 错误: {errors} 条")
            print(f"     - 耗时: {duration:.2f} 秒")
            
            if result.get("total_sheets"):
                print(f"     - Sheet数: {result.get('total_sheets')}")
            if result.get("parsed_sheets"):
                print(f"     - 已解析: {result.get('parsed_sheets')}")
            
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
            print(f"\n  ✗ 导入失败: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "duration": duration
            }
            
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"\n  ✗ 导入异常: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": error_msg,
            "duration": (datetime.now() - start_time).total_seconds()
        }


def verify_import_results(db):
    """验证导入结果"""
    print(f"\n{'='*60}")
    print("验证导入结果")
    print(f"{'='*60}")
    
    # 检查批次
    batches = db.query(ImportBatch).order_by(ImportBatch.id.desc()).limit(10).all()
    print(f"\n最近 {len(batches)} 个批次:")
    for batch in batches:
        status_icon = "✓" if batch.status == "success" else "⚠" if batch.status == "partial" else "✗"
        print(f"  {status_icon} [{batch.id}] {batch.filename}")
        print(f"     状态: {batch.status}, 成功: {batch.success_rows}, 失败: {batch.failed_rows}")
    
    # 检查事实表数据量
    try:
        from app.models.fact_observation import FactObservation
        obs_count = db.query(FactObservation).count()
        print(f"\n  fact_observation 记录数: {obs_count}")
    except:
        pass
    
    try:
        from app.models.fact_futures_daily import FactFuturesDaily
        ftr_count = db.query(FactFuturesDaily).count()
        print(f"  fact_futures_daily 记录数: {ftr_count}")
    except:
        pass
    
    try:
        from app.models.fact_options_daily import FactOptionsDaily
        opt_count = db.query(FactOptionsDaily).count()
        print(f"  fact_options_daily 记录数: {opt_count}")
    except:
        pass
    
    try:
        from app.models.fact_indicator_ts import FactIndicatorTs
        ind_count = db.query(FactIndicatorTs).count()
        print(f"  fact_indicator_ts 记录数: {ind_count}")
    except:
        pass


def main():
    """主函数"""
    print("="*60)
    print("五类数据全量入库自测脚本")
    print("="*60)
    
    # 确定文件路径
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent  # backend -> project root
    docs_dir = project_root / "docs"
    
    # 定义要导入的文件
    files_to_import = [
        {
            "path": docs_dir / "1、价格：钢联自动更新模板.xlsx",
            "expected_type": "GANGLIAN_DAILY",
            "name": "钢联价格模板"
        },
        {
            "path": docs_dir / "2026年2月2日涌益咨询日度数据.xlsx",
            "expected_type": "YONGYI_DAILY",
            "name": "涌益日度数据"
        },
        {
            "path": docs_dir / "lh_ftr.xlsx",
            "expected_type": "LH_FTR",
            "name": "DCE 生猪期货"
        },
        {
            "path": docs_dir / "lh_opt.xlsx",
            "expected_type": "LH_OPT",
            "name": "DCE 生猪期权"
        },
        {
            "path": docs_dir / "2026.1.16-2026.1.22涌益咨询 周度数据.xlsx",
            "expected_type": "YONGYI_WEEKLY",
            "name": "涌益周度数据"
        }
    ]
    
    db = SessionLocal()
    results = []
    
    try:
        # 1. 获取或创建测试用户
        print("\n1. 准备测试用户...")
        user = get_or_create_test_user(db)
        
        # 2. 检查配置文件是否已加载
        print("\n2. 检查配置...")
        from app.models.ingest_profile import IngestProfile
        profiles = db.query(IngestProfile).filter(IngestProfile.is_active == "Y").all()
        if profiles:
            print(f"  ✓ 找到 {len(profiles)} 个活跃配置:")
            for profile in profiles:
                print(f"     - {profile.profile_code} ({profile.dataset_type})")
        else:
            print("  ⚠ 警告：未找到活跃配置，请先运行 load_ingest_profiles.py")
        
        # 3. 逐个导入文件
        print("\n3. 开始导入数据...")
        for i, file_info in enumerate(files_to_import, 1):
            print(f"\n[{i}/{len(files_to_import)}] {file_info['name']}")
            result = import_file(db, file_info["path"], user.id)
            result["file_name"] = file_info["name"]
            result["file_path"] = str(file_info["path"])
            results.append(result)
            
            # 如果失败，自动继续（非交互式环境）
            if not result.get("success"):
                print(f"\n  [WARN] {file_info['name']} import failed, continuing...")
        
        # 4. 验证导入结果
        verify_import_results(db)
        
        # 5. 汇总结果
        print(f"\n{'='*60}")
        print("导入汇总")
        print(f"{'='*60}")
        
        success_count = sum(1 for r in results if r.get("success"))
        total_inserted = sum(r.get("inserted", 0) for r in results)
        total_updated = sum(r.get("updated", 0) for r in results)
        total_errors = sum(r.get("errors", 0) if isinstance(r.get("errors"), int) else 0 for r in results)
        total_duration = sum(r.get("duration", 0) for r in results)
        
        print(f"\n成功导入: {success_count}/{len(results)} 个文件")
        print(f"总新增: {total_inserted} 条")
        print(f"总更新: {total_updated} 条")
        print(f"总错误: {total_errors} 条")
        print(f"总耗时: {total_duration:.2f} 秒")
        
        print("\n详细结果:")
        for result in results:
            status = "✓" if result.get("success") else "✗"
            print(f"  {status} {result.get('file_name')}")
            if result.get("success"):
                print(f"     新增: {result.get('inserted', 0)}, 更新: {result.get('updated', 0)}, 错误: {result.get('errors', 0)}")
            else:
                print(f"     错误: {result.get('error', '未知错误')}")
        
        if success_count == len(results):
            print("\n🎉 所有文件导入成功！")
        else:
            print(f"\n⚠ 有 {len(results) - success_count} 个文件导入失败，请检查错误信息")
        
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
