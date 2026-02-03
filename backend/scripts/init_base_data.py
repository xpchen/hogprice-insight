"""初始化基础数据：dim_region 和 dim_indicator"""
import sys
import os
import io

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import DimRegion, DimIndicator
from app.services.region_mapping_service import rebuild_all_regions


def init_regions(db):
    """初始化区域数据（使用统一的区域映射服务）"""
    result = rebuild_all_regions(db, dry_run=False)
    print(f"已初始化 {result['total']} 个区域（创建: {result['created']}, 更新: {result['updated']}, 跳过: {result['skipped']}）")


def init_indicators(db):
    """初始化指标数据"""
    indicators = [
        # 价格类
        {
            "code": "hog_price_nation",
            "name": "全国出栏均价",
            "freq": "D",
            "unit": "元/公斤",
            "topic": "价格",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "hog_price_province",
            "name": "省份出栏均价",
            "freq": "D",
            "unit": "元/公斤",
            "topic": "价格",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        
        # 屠宰类
        {
            "code": "slaughter_daily",
            "name": "日度屠宰量",
            "freq": "D",
            "unit": "头",
            "topic": "屠宰",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "slaughter_weekly",
            "name": "周度屠宰量",
            "freq": "W",
            "unit": "头",
            "topic": "屠宰",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        
        # 均重类
        {
            "code": "hog_weight_pre_slaughter",
            "name": "宰前均重",
            "freq": "D",
            "unit": "kg",
            "topic": "均重",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "hog_weight_out_week",
            "name": "出栏均重",
            "freq": "W",
            "unit": "kg",
            "topic": "均重",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "hog_weight_scale",
            "name": "规模场出栏均重",
            "freq": "W",
            "unit": "kg",
            "topic": "均重",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "hog_weight_retail",
            "name": "散户出栏均重",
            "freq": "W",
            "unit": "kg",
            "topic": "均重",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "hog_weight_90kg",
            "name": "90kg出栏占比",
            "freq": "W",
            "unit": "%",
            "topic": "均重",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "hog_weight_150kg",
            "name": "150kg出栏占比",
            "freq": "W",
            "unit": "%",
            "topic": "均重",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        
        # 价差类
        {
            "code": "spread_std_fat",
            "name": "标肥价差",
            "freq": "D",
            "unit": "元/公斤",
            "topic": "价差",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "spread_region",
            "name": "区域价差",
            "freq": "D",
            "unit": "元/公斤",
            "topic": "价差",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "spread_hog_carcass",
            "name": "毛白价差",
            "freq": "D",
            "unit": "元/公斤",
            "topic": "价差",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        
        # 冻品类
        {
            "code": "frozen_capacity_rate",
            "name": "冻品库容率",
            "freq": "W",
            "unit": "%",
            "topic": "冻品",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        
        # 产业链类
        {
            "code": "profit_breeding",
            "name": "养殖利润",
            "freq": "W",
            "unit": "元/头",
            "topic": "产业链",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
        {
            "code": "feed_price_full",
            "name": "全价料价格",
            "freq": "W",
            "unit": "元/吨",
            "topic": "产业链",
            "source_code": "YONGYI",
            "calc_method": "RAW"
        },
    ]
    
    for ind in indicators:
        existing = db.query(DimIndicator).filter(DimIndicator.indicator_code == ind["code"]).first()
        if not existing:
            indicator = DimIndicator(
                indicator_code=ind["code"],
                indicator_name=ind["name"],
                freq=ind["freq"],
                unit=ind["unit"],
                topic=ind["topic"],
                source_code=ind["source_code"],
                calc_method=ind["calc_method"]
            )
            db.add(indicator)
    
    db.commit()
    print(f"已初始化 {len(indicators)} 个指标")


def main():
    """执行初始化"""
    db = SessionLocal()
    
    try:
        print("开始初始化基础数据...")
        print("=" * 50)
        
        print("\n1. 初始化区域数据...")
        init_regions(db)
        
        print("\n2. 初始化指标数据...")
        init_indicators(db)
        
        print("\n" + "=" * 50)
        print("初始化完成！")
        
    except Exception as e:
        print(f"\n初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
