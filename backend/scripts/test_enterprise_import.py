"""测试企业集团数据导入"""
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# 添加项目根目录到路径
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.ingestors.enterprise_ingestor import import_enterprise_data
from app.services.ingestors.profile_loader import load_profile_from_json
from app.models.dim_source import DimSource
import json

def test_import():
    """测试导入企业集团数据"""
    db: Session = SessionLocal()
    
    try:
        # 1. 确保数据源存在
        source = db.query(DimSource).filter(DimSource.source_code == "ENTERPRISE").first()
        if not source:
            source = DimSource(
                source_code="ENTERPRISE",
                source_name="企业集团出栏跟踪",
                source_type="ENTERPRISE"
            )
            db.add(source)
            db.commit()
            print("[OK] 创建数据源: ENTERPRISE")
        
        # 2. 加载profile配置
        profile_path = script_dir.parent / "docs" / "ingest_profile_enterprise_daily_v1.json"
        if profile_path.exists():
            try:
                profile = load_profile_from_json(db, str(profile_path))
                print(f"[OK] 加载profile配置: {profile.profile_code}")
            except Exception as e:
                print(f"[WARN] Profile配置加载失败（可能已存在）: {e}")
        else:
            print(f"[WARN] Profile配置文件不存在: {profile_path}")
        
        # 3. 查找Excel文件
        excel_file = script_dir.parent / "docs" / "生猪" / "集团企业" / "3.1、集团企业出栏跟踪【分省区】.xlsx"
        if not excel_file.exists():
            print(f"[ERROR] Excel文件不存在: {excel_file}")
            return
        
        print(f"\n开始导入文件: {excel_file.name}")
        
        # 4. 读取文件内容
        with open(excel_file, 'rb') as f:
            file_content = f.read()
        
        # 5. 执行导入
        result = import_enterprise_data(
            db=db,
            file_content=file_content,
            filename=excel_file.name,
            uploader_id=1,
            source_code="ENTERPRISE"
        )
        
        # 6. 显示结果
        print("\n导入结果:")
        print(f"  成功: {result.get('success', False)}")
        print(f"  插入: {result.get('inserted', 0)} 条")
        print(f"  更新: {result.get('updated', 0)} 条")
        errors = result.get('errors', [])
        if isinstance(errors, list):
            print(f"  错误: {len(errors)} 个")
        else:
            print(f"  错误: {errors}")
        
        if result.get('errors'):
            print("\n错误列表:")
            for error in result.get('errors', [])[:10]:  # 只显示前10个错误
                print(f"  - {error}")
        
        # 7. 查询导入的数据
        from app.models.fact_observation import FactObservation
        from app.models.dim_metric import DimMetric
        from sqlalchemy import func
        
        # 查询CR5数据（metric_key存储在parse_json中）
        cr5_metrics = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key').like('CR5%')
        ).all()
        
        if cr5_metrics:
            total_count = 0
            for metric in cr5_metrics:
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == metric.id
                ).count()
                total_count += count
            print(f"\n[OK] CR5指标数据: {total_count} 条（{len(cr5_metrics)} 个指标）")
        
        # 查询西南数据
        sw_metrics = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key').like('SOUTHWEST%')
        ).all()
        
        if sw_metrics:
            total_count = 0
            for metric in sw_metrics:
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == metric.id
                ).count()
                total_count += count
            print(f"[OK] 西南指标数据: {total_count} 条（{len(sw_metrics)} 个指标）")
        
        print("\n测试完成！")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] 导入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_import()
