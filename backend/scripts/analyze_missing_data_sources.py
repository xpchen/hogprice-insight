"""
分析缺失的官方数据源
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import json

script_dir = Path(__file__).parent.parent
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.dim_source import DimSource
from app.models.raw_sheet import RawSheet
from app.models.raw_file import RawFile

def analyze_missing_sources():
    """分析缺失的数据源"""
    print("=" * 80)
    print("分析缺失的官方数据源")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 检查已注册的数据源
        print("\n1. 已注册的数据源（dim_source表）:")
        sources = db.query(DimSource).all()
        for source in sources:
            print(f"  - {source.source_code}: {source.source_name} ({source.source_type})")
        
        # 2. 检查raw_file中的数据源
        print("\n\n2. raw_file中的数据源（通过文件名推断）:")
        raw_files = db.query(RawFile).distinct(RawFile.filename).limit(50).all()
        source_patterns = {}
        
        for rf in raw_files:
            filename = rf.filename or ""
            if "涌益" in filename or "YONGYI" in filename.upper():
                source_patterns["涌益咨询"] = source_patterns.get("涌益咨询", 0) + 1
            elif "钢联" in filename or "GANGLIAN" in filename.upper() or "MYSTEEL" in filename.upper():
                source_patterns["钢联"] = source_patterns.get("钢联", 0) + 1
            elif "DCE" in filename.upper() or "大连" in filename:
                source_patterns["大连商品交易所"] = source_patterns.get("大连商品交易所", 0) + 1
            elif "协会" in filename or "ASSOCIATION" in filename.upper():
                source_patterns["协会"] = source_patterns.get("协会", 0) + 1
            elif "NYB" in filename.upper():
                source_patterns["NYB"] = source_patterns.get("NYB", 0) + 1
            elif "农业部" in filename or "AGRICULTURE" in filename.upper():
                source_patterns["农业部"] = source_patterns.get("农业部", 0) + 1
            elif "统计局" in filename or "STATISTICS" in filename.upper():
                source_patterns["统计局"] = source_patterns.get("统计局", 0) + 1
            elif "生猪产业" in filename:
                source_patterns["生猪产业数据"] = source_patterns.get("生猪产业数据", 0) + 1
        
        for source_name, count in source_patterns.items():
            print(f"  - {source_name}: {count} 个文件")
        
        # 3. 检查E2.多渠道汇总中提到的数据源
        print("\n\n3. E2.多渠道汇总需求中提到的数据源:")
        required_sources = {
            "涌益": "涌益咨询周度数据",
            "钢联": "钢联模板",
            "协会": "【生猪产业数据】- 02.协会猪料",
            "NYB": "【生猪产业数据】- NYB"
        }
        
        for source_name, description in required_sources.items():
            # 检查是否有对应的sheet
            if source_name == "协会":
                sheets = db.query(RawSheet).join(RawFile).filter(
                    RawSheet.sheet_name.like("%协会%")
                ).all()
            elif source_name == "NYB":
                sheets = db.query(RawSheet).join(RawFile).filter(
                    RawSheet.sheet_name.like("%NYB%")
                ).all()
            else:
                sheets = []
            
            if sheets:
                print(f"  ✓ {source_name}: {description}")
                print(f"    找到 {len(sheets)} 个相关sheet")
                for sheet in sheets[:3]:
                    print(f"      - {sheet.sheet_name}")
            else:
                print(f"  ✗ {source_name}: {description} (未找到)")
        
        # 4. 检查其他可能的官方数据源
        print("\n\n4. 其他可能的官方数据源（需要确认）:")
        potential_sources = [
            {
                "name": "农业农村部",
                "description": "农业农村部官方统计数据（能繁母猪存栏、生猪存栏等）",
                "url_pattern": "可能来自：http://www.moa.gov.cn/",
                "data_type": "月度统计数据"
            },
            {
                "name": "国家统计局",
                "description": "国家统计局官方统计数据",
                "url_pattern": "可能来自：http://www.stats.gov.cn/",
                "data_type": "月度/季度统计数据"
            },
            {
                "name": "中国畜牧业协会",
                "description": "中国畜牧业协会统计数据",
                "url_pattern": "可能来自：http://www.caaa.cn/",
                "data_type": "行业统计数据"
            },
            {
                "name": "中国饲料工业协会",
                "description": "中国饲料工业协会统计数据（饲料产量等）",
                "url_pattern": "可能来自：http://www.chinafeed.org.cn/",
                "data_type": "月度统计数据"
            },
            {
                "name": "海关总署",
                "description": "海关总署进出口数据（猪肉进口等）",
                "url_pattern": "可能来自：http://www.customs.gov.cn/",
                "data_type": "月度进出口数据"
            }
        ]
        
        for source in potential_sources:
            print(f"\n  - {source['name']}")
            print(f"    描述: {source['description']}")
            print(f"    数据类型: {source['data_type']}")
            print(f"    可能来源: {source['url_pattern']}")
        
        # 5. 检查文档中提到的数据源
        print("\n\n5. 文档中提到的数据源:")
        docs_dir = Path(script_dir.parent) / "docs"
        
        # 查找是否有"生猪产业数据"相关的文件
        industry_data_files = list(docs_dir.glob("*生猪产业*.xlsx")) + list(docs_dir.glob("*生猪产业*.zip"))
        if industry_data_files:
            print(f"  找到 {len(industry_data_files)} 个'生猪产业数据'相关文件:")
            for f in industry_data_files:
                print(f"    - {f.name}")
        else:
            print("  ✗ 未找到'生猪产业数据'相关文件")
        
        # 查找是否有其他官方数据文件
        official_keywords = ["农业部", "统计局", "协会", "NYB"]
        for keyword in official_keywords:
            files = list(docs_dir.glob(f"*{keyword}*.xlsx")) + list(docs_dir.glob(f"*{keyword}*.zip"))
            if files:
                print(f"\n  找到 {len(files)} 个'{keyword}'相关文件:")
                for f in files:
                    print(f"    - {f.name}")
        
    finally:
        db.close()

if __name__ == "__main__":
    analyze_missing_sources()
