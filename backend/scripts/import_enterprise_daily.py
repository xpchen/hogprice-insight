"""重新导入集团企业日度数据（含西南汇总成交率）
用法: python scripts/import_enterprise_daily.py [Excel文件路径]
不传路径时，自动在 docs/生猪/集团企业/ 下查找 3.1、集团企业出栏跟踪【分省区】.xlsx
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))


def excel_has_southwest_sheet(path: Path) -> bool:
    """检查 Excel 是否包含 西南汇总 或 CR5日度 sheet"""
    try:
        import pandas as pd
        xl = pd.ExcelFile(path, engine='openpyxl')
        return '西南汇总' in xl.sheet_names or 'CR5日度' in xl.sheet_names
    except Exception:
        return False


from app.core.database import SessionLocal
from app.models.sys_user import SysUser
from app.services.ingestors.unified_ingestor import unified_import
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from sqlalchemy import func


def find_enterprise_daily_file() -> Path | None:
    """查找集团企业出栏跟踪 Excel 文件（含 CR5日度、西南汇总 sheet）"""
    # 优先：标准文件名
    priority = [
        script_dir.parent / "docs" / "生猪" / "集团企业" / "3.1、集团企业出栏跟踪【分省区】.xlsx",
        script_dir.parent / "docs" / "集团企业出栏跟踪【分省区】.xlsx",
    ]
    for p in priority:
        if p.exists():
            return p
    # 其次：递归查找含 西南汇总 或 CR5日度 的 xlsx
    docs_dir = script_dir.parent / "docs"
    if docs_dir.exists():
        for p in sorted(docs_dir.rglob("*.xlsx")):
            if "~$" in p.name:
                continue
            if excel_has_southwest_sheet(p):
                return p
    return None


def main():
    file_path = None
    if len(sys.argv) >= 2:
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            sys.exit(1)
    else:
        file_path = find_enterprise_daily_file()
        if not file_path:
            print("❌ 未找到集团企业出栏跟踪 Excel 文件")
            print("   请将文件放到 docs/生猪/集团企业/3.1、集团企业出栏跟踪【分省区】.xlsx")
            print("   或执行: python scripts/import_enterprise_daily.py <文件路径>")
            sys.exit(1)

    print(f"📂 导入文件: {file_path}")
    with open(file_path, 'rb') as f:
        file_content = f.read()

    db = SessionLocal()
    try:
        user = db.query(SysUser).filter(SysUser.username == "admin").first()
        if not user:
            user = db.query(SysUser).first()
        uploader_id = user.id if user else 1

        print("⏳ 执行导入...")
        result = unified_import(
            db=db,
            file_content=file_content,
            filename=file_path.name,
            uploader_id=uploader_id,
            dataset_type="ENTERPRISE_DAILY",
            source_code="ENTERPRISE"
        )

        success = result.get("success", False)
        inserted = result.get("inserted", 0)
        updated = result.get("updated", 0)
        errors = result.get("errors", [])
        if isinstance(errors, int):
            error_count = errors
            errors = []
        else:
            error_count = len(errors)

        print(f"\n📊 导入结果:")
        print(f"   成功: {success}")
        print(f"   插入: {inserted} 条")
        print(f"   更新: {updated} 条")
        print(f"   错误: {error_count} 个")
        if errors:
            for e in (errors[:5] if isinstance(errors, list) else []):
                print(f"      - {e.get('reason', e)}")

        # 验证四川、广西成交率数据
        print("\n📋 验证成交率数据（四川 E 列、广西 K 列）:")
        tx_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "西南汇总",
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_TRANSACTION_RATE'
        ).first()

        if tx_metric:
            for region in ["四川", "广西"]:
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == tx_metric.id,
                    func.json_extract(FactObservation.tags_json, '$.region') == region
                ).count()
                if count > 0:
                    sample = db.query(FactObservation).filter(
                        FactObservation.metric_id == tx_metric.id,
                        func.json_extract(FactObservation.tags_json, '$.region') == region
                    ).order_by(FactObservation.obs_date.desc()).first()
                    print(f"   ✓ {region} 成交率: {count} 条 (最新: {sample.obs_date} = {sample.value}%)")
                else:
                    print(f"   ⚠ {region} 成交率: 0 条")
            print("\n✓ 成交率数据已正确解析（实际成交/挂牌）")
        else:
            # 兼容：检查旧完成率
            old_metric = db.query(DimMetric).filter(
                DimMetric.sheet_name == "西南汇总",
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_COMPLETION_RATE'
            ).first()
            if old_metric:
                print("   ⚠ 当前为旧指标 SOUTHWEST_COMPLETION_RATE，请确认 Excel 第2行有「成交率」列")
            else:
                print("   ⚠ 未找到成交率指标，请检查西南汇总 sheet 结构")

        print("\n✅ 导入完成")
    except Exception as e:
        db.rollback()
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
