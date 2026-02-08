"""
测试导入白条市场跟踪数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.ingestors.unified_ingestor import unified_import
from app.services.ingestors.profile_loader import load_profile_from_json
from app.models.dim_source import DimSource

def test_import():
    """测试导入白条市场跟踪数据"""
    print("=" * 80)
    print("测试导入白条市场跟踪数据")
    print("=" * 80)
    
    # 文件路径
    docs_dir = script_dir.parent / "docs" / "生猪"
    file_path = docs_dir / "3.3、白条市场跟踪.xlsx"
    
    if not file_path.exists():
        print(f"\n文件不存在: {file_path}")
        return
    
    print(f"\n文件路径: {file_path}")
    
    # 读取文件
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    # 加载profile
    profile_path = script_dir.parent / "docs" / "ingest_profile_white_strip_market_v1.json"
    if not profile_path.exists():
        print(f"\nProfile文件不存在: {profile_path}")
        return
    
    print(f"\n加载Profile: {profile_path.name}")
    
    # 确保数据源存在
    db: Session = SessionLocal()
    try:
        source = db.query(DimSource).filter(DimSource.source_code == "WHITE_STRIP_MARKET").first()
        if not source:
            source = DimSource(
                source_code="WHITE_STRIP_MARKET",
                source_name="白条市场跟踪",
                source_type="WHITE_STRIP_MARKET"
            )
            db.add(source)
            db.commit()
            print("[OK] 创建数据源: WHITE_STRIP_MARKET")
        
        # 加载profile配置
        try:
            profile = load_profile_from_json(db, str(profile_path))
            print(f"✓ Profile已加载: {profile.profile_code} ({len(profile.sheets)} sheets)")
        except Exception as e:
            print(f"[WARN] Profile配置加载失败（可能已存在）: {e}")
            # 尝试从数据库获取
            from app.services.ingestors.profile_loader import get_profile_by_code
            profile = get_profile_by_code(db, "WHITE_STRIP_MARKET_V1")
            if not profile:
                print("Profile加载失败")
                return
            print(f"✓ 从数据库加载Profile: {profile.profile_code}")
    finally:
        db.close()
    
    # 执行导入
    db = SessionLocal()
    try:
        print(f"\n开始导入文件: {file_path.name}")
        result = unified_import(
            db=db,
            file_content=file_content,
            filename=file_path.name,
            uploader_id=1,
            dataset_type=profile.dataset_type,
            source_code=profile.source_code
        )
        
        print(f"\n导入结果:")
        print(f"  成功: {result.get('success', False)}")
        if result.get('success'):
            print(f"  插入: {result.get('inserted', 0)} 条")
            print(f"  更新: {result.get('updated', 0)} 条")
            if result.get('errors'):
                if isinstance(result['errors'], list):
                    print(f"  错误: {len(result['errors'])} 个")
                    for error in result['errors'][:5]:
                        print(f"    - {error}")
                else:
                    print(f"  错误: {result['errors']}")
        else:
            print(f"  错误: {result.get('errors', '未知错误')}")
            
    except Exception as e:
        print(f"\n导入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_import()
