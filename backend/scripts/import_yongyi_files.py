"""
导入涌益咨询数据文件
- 涌益咨询 周度数据.xlsx
- 涌益咨询日度数据.xlsx
使用统一导入工作流
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
from sqlalchemy.orm import Session

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.services.ingestors.unified_ingestor import unified_import
from app.models.sys_user import SysUser

def get_or_create_admin_user(db: Session) -> SysUser:
    """获取或创建admin用户"""
    user = db.query(SysUser).filter(SysUser.username == "admin").first()
    if not user:
        user = SysUser(
            username="admin",
            email="admin@example.com",
            full_name="系统管理员",
            is_active=True,
            is_superuser=True
        )
        db.add(user)
        db.flush()
    return user

def import_yongyi_files():
    """导入涌益咨询数据文件"""
    # 文件路径
    project_root = script_dir.parent
    weekly_file = project_root / "docs" / "生猪" / "涌益生猪项目数据库_2" / "涌益生猪项目数据库" / "涌益咨询 周度数据.xlsx"
    daily_file = project_root / "docs" / "生猪" / "涌益生猪项目数据库_2" / "涌益生猪项目数据库" / "涌益咨询日度数据.xlsx"
    
    files_to_import = [
        {
            "path": weekly_file,
            "name": "涌益咨询 周度数据",
            "dataset_type": "YONGYI_WEEKLY",
            "source_code": "YONGYI"
        },
        {
            "path": daily_file,
            "name": "涌益咨询日度数据",
            "dataset_type": "YONGYI_DAILY",
            "source_code": "YONGYI"
        }
    ]
    
    print("=" * 80)
    print("导入涌益咨询数据文件")
    print("=" * 80)
    
    # 检查文件是否存在
    for file_info in files_to_import:
        if not file_info["path"].exists():
            print(f"\n❌ 文件不存在: {file_info['path']}")
            return
    
    db: Session = SessionLocal()
    try:
        # 获取或创建admin用户
        user = get_or_create_admin_user(db)
        print(f"\n✓ 使用用户: {user.username} (ID: {user.id})")
        
        # 导入每个文件
        results = []
        for file_info in files_to_import:
            print(f"\n{'='*80}")
            print(f"导入文件: {file_info['name']}")
            print(f"文件路径: {file_info['path']}")
            print(f"数据集类型: {file_info['dataset_type']}")
            print(f"{'='*80}")
            
            try:
                # 读取文件内容
                with open(file_info["path"], 'rb') as f:
                    file_content = f.read()
                
                # 调用统一导入工作流
                result = unified_import(
                    db=db,
                    file_content=file_content,
                    filename=file_info["path"].name,
                    uploader_id=user.id,
                    dataset_type=file_info["dataset_type"],
                    source_code=file_info["source_code"]
                )
                
                results.append({
                    "file": file_info["name"],
                    "success": True,
                    "result": result
                })
                
                print(f"\n✓ 导入成功!")
                print(f"  批次ID: {result.get('batch_id')}")
                print(f"  总sheet数: {result.get('total_sheets', 0)}")
                print(f"  已解析sheet数: {result.get('parsed_sheets', 0)}")
                print(f"  新增记录数: {result.get('inserted_count', 0)}")
                print(f"  更新记录数: {result.get('updated_count', 0)}")
                print(f"  错误数: {result.get('error_count', 0)}")
                
                if result.get('errors'):
                    print(f"\n  错误详情:")
                    for error in result['errors'][:10]:  # 只显示前10个错误
                        print(f"    - {error}")
                    if len(result['errors']) > 10:
                        print(f"    ... 还有 {len(result['errors']) - 10} 个错误")
                
            except Exception as e:
                print(f"\n❌ 导入失败: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    "file": file_info["name"],
                    "success": False,
                    "error": str(e)
                })
                db.rollback()
                # 继续导入下一个文件
                continue
        
        # 汇总结果
        print(f"\n{'='*80}")
        print("导入汇总")
        print(f"{'='*80}")
        
        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count
        
        print(f"\n成功: {success_count} 个文件")
        print(f"失败: {fail_count} 个文件")
        
        for result in results:
            status = "✓" if result["success"] else "❌"
            print(f"\n{status} {result['file']}")
            if result["success"]:
                r = result["result"]
                print(f"  新增: {r.get('inserted_count', 0)}, 更新: {r.get('updated_count', 0)}, 错误: {r.get('error_count', 0)}")
            else:
                print(f"  错误: {result.get('error', 'Unknown error')}")
        
        db.commit()
        print(f"\n✓ 所有导入操作完成")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 导入过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import_yongyi_files()
