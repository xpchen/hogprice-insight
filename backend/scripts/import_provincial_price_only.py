"""仅导入各省份出栏均价（贵州、四川、云南、广东、广西、江苏、内蒙古）
用于 C3 重点区域升贴水 的省份现货价格数据
数据来源：钢联「分省区猪价」sheet
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import get_db
from scripts.extract_ganglian_price_data import GanglianPriceExtractor

def main():
    workspace_root = project_root.parent
    ganglian_file = workspace_root / "docs" / "1、价格：钢联自动更新模板-新增.xlsx"
    if not ganglian_file.exists():
        ganglian_file = workspace_root / "docs" / "1、价格：钢联自动更新模板.xlsx"
    if not ganglian_file.exists():
        print(f"错误: 未找到文件 {ganglian_file}")
        return

    db = next(get_db())
    try:
        extractor = GanglianPriceExtractor(db, ganglian_file)
        batch = extractor._create_batch()
        result = extractor._extract_provincial_price(batch.id)
        db.commit()
        print(f"\n导入完成: 批次ID={batch.id}")
        print(f"总计插入: {result['inserted']} 条")
        for province, count in result.get('provinces', {}).items():
            print(f"  {province}: {count} 条")
    except Exception as e:
        db.rollback()
        print(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
