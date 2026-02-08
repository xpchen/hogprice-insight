"""导入包含'汇总'sheet的文件（3.2、集团企业月度数据跟踪.xlsx）"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import zipfile

# 添加项目根目录到路径
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.ingestors.enterprise_ingestor import import_enterprise_data
from app.services.ingestors.profile_loader import load_profile_from_json
from app.models.dim_source import DimSource
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from sqlalchemy import func

def import_summary_sheet():
    """导入包含'汇总'sheet的文件"""
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
                print(f"[OK] Profile已加载: {profile.profile_code}")
            except Exception as e:
                print(f"[WARN] Profile配置加载失败（可能已存在）: {e}")
        else:
            print(f"[ERROR] Profile配置文件不存在: {profile_path}")
            return
        
        # 3. 查找Excel文件（从zip中解压或直接使用）
        zip_path = script_dir.parent / "docs" / "生猪" / "数据库模板02：集团企业.zip"
        excel_filename = "3.2、集团企业月度数据跟踪.xlsx"
        
        # 检查是否已经解压
        extracted_path = script_dir.parent / "docs" / "生猪" / "集团企业" / excel_filename
        file_content = None
        
        if extracted_path.exists():
            print(f"[OK] 找到已解压的文件: {extracted_path}")
            with open(extracted_path, 'rb') as f:
                file_content = f.read()
        elif zip_path.exists():
            print(f"[OK] 从zip文件中提取: {excel_filename}")
            with zipfile.ZipFile(zip_path, 'r') as z:
                if excel_filename in z.namelist():
                    file_content = z.read(excel_filename)
                    print(f"[OK] 成功读取zip文件内容")
                else:
                    print(f"[ERROR] zip文件中没有找到: {excel_filename}")
                    print(f"  zip文件中的文件列表:")
                    for name in z.namelist():
                        print(f"    - {name}")
                    return
        else:
            print(f"[ERROR] 找不到文件或zip文件")
            print(f"  检查路径:")
            print(f"    - zip文件: {zip_path}")
            print(f"    - 解压文件: {extracted_path}")
            return
        
        if not file_content:
            print("[ERROR] 无法读取文件内容")
            return
        
        print(f"\n开始导入文件: {excel_filename}")
        print(f"文件大小: {len(file_content)} 字节")
        
        # 4. 执行导入
        result = import_enterprise_data(
            db=db,
            file_content=file_content,
            filename=excel_filename,
            uploader_id=1,
            source_code="ENTERPRISE"
        )
        
        # 5. 显示结果
        print("\n" + "=" * 80)
        print("导入结果:")
        print("=" * 80)
        print(f"  成功: {result.get('success', False)}")
        print(f"  插入: {result.get('inserted', 0)} 条")
        print(f"  更新: {result.get('updated', 0)} 条")
        errors = result.get('errors', [])
        if isinstance(errors, list):
            print(f"  错误: {len(errors)} 个")
            if errors:
                print("\n错误列表（前10个）:")
                for error in errors[:10]:
                    print(f"    - {error}")
        else:
            print(f"  错误: {errors}")
        
        # 6. 查询导入的数据
        print("\n" + "=" * 80)
        print("查询导入的数据:")
        print("=" * 80)
        
        # 查询"汇总"sheet的指标
        summary_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        if summary_metrics:
            print(f"\n[OK] 找到 {len(summary_metrics)} 个'汇总'sheet的指标:")
            total_count = 0
            for metric in summary_metrics:
                metric_key = metric.parse_json.get('metric_key') if metric.parse_json else None
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == metric.id
                ).count()
                total_count += count
                print(f"  - {metric.metric_name} ({metric_key}): {count} 条")
            print(f"\n[OK] '汇总'sheet总数据: {total_count} 条")
        else:
            print("\n[WARN] 未找到'汇总'sheet的指标")
        
        # 查询特定省份的数据（广东、四川、贵州）
        if summary_metrics:
            print("\n查询特定省份的数据（广东、四川、贵州）:")
            target_provinces = ['广东', '四川', '贵州']
            metric_ids = [m.id for m in summary_metrics]
            
            for province in target_provinces:
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id.in_(metric_ids),
                    func.json_extract(FactObservation.tags_json, '$.region') == province
                ).count()
                print(f"  - {province}: {count} 条")
        
        print("\n导入完成！")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] 导入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import_summary_sheet()
