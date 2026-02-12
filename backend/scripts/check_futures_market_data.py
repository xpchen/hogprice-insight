# -*- coding: utf-8 -*-
"""
期货市场相关页面（C1-C4）数据检查
http://localhost:5173/futures-market/*

C1 升贴水 /premium
C2 月间价差 /calendar-spread
C3 区域升贴水 /region-premium
C4 波动率 /volatility
"""
import sys
import io
from pathlib import Path
from datetime import date

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.fact_futures_daily import FactFuturesDaily
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric


def main():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("期货市场页面（C1-C4）数据检查")
        print("=" * 70)

        # 1. fact_futures_daily
        ftr_count = db.query(func.count(FactFuturesDaily.id)).scalar()
        ftr_min = db.query(func.min(FactFuturesDaily.trade_date)).scalar()
        ftr_max = db.query(func.max(FactFuturesDaily.trade_date)).scalar()

        print("\n【1. 期货日度数据 fact_futures_daily】")
        print(f"    记录数: {ftr_count}")
        if ftr_count > 0:
            print(f"    日期范围: {ftr_min} ~ {ftr_max}")
            # 估算交易日数
            if ftr_min and ftr_max:
                delta = (ftr_max - ftr_min).days
                print(f"    跨度: 约 {delta} 天")
                if ftr_count < 1000:
                    print("    ⚠ 数据较少，建议导入 lh_ftr.xlsx 更多历史数据")
        else:
            print("    ❌ 无数据！请先导入 lh_ftr.xlsx（日历史行情 sheet）")
            print("       导入方式: 数据导入 -> 选择 LH_FTR -> 上传 lh_ftr.xlsx")

        # 2. fact_observation（现货价格，用于 C1/C3 升贴水）
        prov_metric_ids = [r[0] for r in db.query(DimMetric.id).filter(
            DimMetric.sheet_name == "分省区猪价",
            DimMetric.freq.in_(["D", "daily"])
        ).all()]
        spot_count = (db.query(func.count(FactObservation.id)).filter(
            FactObservation.metric_id.in_(prov_metric_ids)
        ).scalar() or 0) if prov_metric_ids else 0

        # 全国均价指标
        nation_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价",
            DimMetric.freq.in_(["D", "daily"]),
            DimMetric.raw_header.like("%中国%")
        ).first()
        if nation_metric:
            nation_count = db.query(func.count(FactObservation.id)).filter(
                FactObservation.metric_id == nation_metric.id
            ).scalar() or 0
            nation_range = db.query(func.min(FactObservation.obs_date), func.max(FactObservation.obs_date)).filter(
                FactObservation.metric_id == nation_metric.id
            ).first()
        else:
            nation_count = 0
            nation_range = (None, None)

        print("\n【2. 现货价格 fact_observation（C1/C3 升贴水）】")
        print(f"    分省区猪价-日度相关观测数: {spot_count}")
        if nation_metric:
            print(f"    全国均价(中国): {nation_count} 条")
            if nation_range[0] and nation_range[1]:
                print(f"    日期范围: {nation_range[0]} ~ {nation_range[1]}")
        if spot_count == 0:
            print("    ❌ 无现货价格！请导入钢联价格模板或分省区猪价数据")

        # 3. 时间重叠（期货与现货）
        if ftr_count > 0 and nation_count > 0 and ftr_min and ftr_max and nation_range[0] and nation_range[1]:
            overlap_start = max(ftr_min, nation_range[0])
            overlap_end = min(ftr_max, nation_range[1])
            if overlap_start <= overlap_end:
                overlap_days = (overlap_end - overlap_start).days
                print(f"\n【3. 期货与现货时间重叠】")
                print(f"    重叠日期: {overlap_start} ~ {overlap_end}（约{overlap_days}天）")
                if overlap_days < 30:
                    print("    ⚠ 重叠天数较少，升贴水图可能较空")
            else:
                print("\n【3. 期货与现货】")
                print("    ❌ 无时间重叠，升贴水无法计算")

        # 4. 波动率可计算性
        print("\n【4. 波动率（C4）】")
        if ftr_count < 20:
            print(f"    期货仅 {ftr_count} 条，不足 20 个交易日，无法计算 10 日波动率")
            print("    建议: 导入至少 2 个月以上的期货日度数据")
        else:
            # 检查各合约
            for month in [1, 3, 5, 7, 9, 11]:
                ms = f"{month:02d}"
                cnt = db.query(func.count(FactFuturesDaily.id)).filter(
                    FactFuturesDaily.contract_code.like(f"%{ms}")
                ).scalar()
                dates = db.query(FactFuturesDaily.trade_date).filter(
                    FactFuturesDaily.contract_code.like(f"%{ms}")
                ).distinct().count()
                if dates >= 20:
                    print(f"    {ms}合约: {cnt}条, {dates}个交易日 ✓ 可计算波动率")
                else:
                    print(f"    {ms}合约: {cnt}条, {dates}个交易日（需≥20）")

        # 5. 导入建议
        print("\n" + "=" * 70)
        print("【数据导入建议】")
        print("=" * 70)
        if ftr_count < 500:
            print("1. 期货数据(lh_ftr.xlsx): 当前数据较少，建议准备含多年历史的 lh_ftr.xlsx")
            print("   - 需包含「日历史行情」或「历史行情」sheet")
            print("   - 列: 合约名称、交易日期、收盘价、结算价、持仓量 等")
        if spot_count < 500:
            print("2. 现货数据: 需导入钢联价格模板(分省区猪价)或等效数据")
        print("\n运行检查: python scripts/check_premium_data.py  # 升贴水")
        print("          python scripts/check_volatility_data.py  # 波动率")

    finally:
        db.close()


if __name__ == "__main__":
    main()
