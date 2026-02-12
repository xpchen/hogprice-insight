"""
导入涌益咨询数据文件
支持日度和周度数据导入
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
from app.models.sys_user import SysUser
from app.services.ingestors.unified_ingestor import unified_import

def get_or_create_test_user(db: Session) -> SysUser:
    """获取或创建测试用户"""
    user = db.query(SysUser).filter(SysUser.username == "admin").first()
    if not user:
        user = SysUser(
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            is_active=True,
            is_superuser=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def import_yongyi_file(file_path: Path, dataset_type: str, file_name: str):
    """导入单个涌益文件"""
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    print(f"\n{'='*80}")
    print(f"导入文件: {file_name}")
    print(f"文件路径: {file_path}")
    print(f"数据类型: {dataset_type}")
    print(f"{'='*80}")
    
    db = SessionLocal()
    try:
        # 获取或创建用户
        user = get_or_create_test_user(db)
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        print(f"\n📁 文件信息:")
        print(f"  文件名: {file_path.name}")
        print(f"  文件大小: {len(file_content) / 1024 / 1024:.2f} MB")
        
        # 使用统一导入工作流
        print(f"\n🚀 开始导入...")
        try:
            result = unified_import(
                db=db,
                file_content=file_content,
                filename=file_path.name,
                uploader_id=user.id,
                dataset_type=dataset_type,
                source_code=None  # 自动推断
            )
        except ValueError as e:
            # 捕获解析器类型错误，但继续处理其他sheet
            if "未知的解析器类型" in str(e) or "未知的解析器类型" in repr(e):
                print(f"\n⚠️  遇到不支持的解析器类型，但部分数据可能已导入")
                print(f"  错误: {e}")
                # 尝试获取部分结果
                result = {
                    "batch_id": None,
                    "total_sheets": 0,
                    "parsed_sheets": 0,
                    "inserted_count": 0,
                    "updated_count": 0,
                    "error_count": 1,
                    "errors": [str(e)]
                }
            else:
                raise
        
        print(f"\n✅ 导入完成!")
        print(f"  批次ID: {result.get('batch_id')}")
        print(f"  总sheet数: {result.get('total_sheets', 0)}")
        print(f"  已解析sheet数: {result.get('parsed_sheets', 0)}")
        print(f"  新增记录数: {result.get('inserted_count', 0)}")
        print(f"  更新记录数: {result.get('updated_count', 0)}")
        print(f"  错误数: {result.get('error_count', 0)}")
        
        if result.get('errors'):
            print(f"\n⚠️  错误信息:")
            for error in result['errors'][:10]:  # 只显示前10个错误
                print(f"  - {error}")
            if len(result['errors']) > 10:
                print(f"  ... 还有 {len(result['errors']) - 10} 个错误")
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """主函数"""
    print("=" * 80)
    print("涌益咨询数据导入脚本")
    print("=" * 80)
    
    # 确定文件路径
    project_root = script_dir.parent
    docs_dir = project_root / "docs" / "生猪" / "涌益生猪项目数据库_2" / "涌益生猪项目数据库"
    
    # 定义要导入的文件
    files_to_import = [
        {
            "path": docs_dir / "涌益咨询 周度数据.xlsx",
            "dataset_type": "YONGYI_WEEKLY",
            "name": "涌益咨询 周度数据"
        },
        {
            "path": docs_dir / "涌益咨询日度数据.xlsx",
            "dataset_type": "YONGYI_DAILY",
            "name": "涌益咨询日度数据"
        }
    ]
    
    results = []
    
    for file_info in files_to_import:
        success = import_yongyi_file(
            file_info["path"],
            file_info["dataset_type"],
            file_info["name"]
        )
        results.append({
            "name": file_info["name"],
            "success": success
        })
    
    # 汇总结果
    print(f"\n{'='*80}")
    print("导入汇总")
    print(f"{'='*80}")
    
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    
    for result in results:
        status = "✅ 成功" if result["success"] else "❌ 失败"
        print(f"  {status} - {result['name']}")
    
    print(f"\n总计: {success_count}/{total_count} 个文件导入成功")
    
    if success_count == total_count:
        print("\n🎉 所有文件导入成功!")
    else:
        print(f"\n⚠️  有 {total_count - success_count} 个文件导入失败，请检查错误信息")

if __name__ == "__main__":
    main()
