"""检查省份升贴水与升贴水比率：合约升贴水有数据，升贴水比率无数据的原因"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app.core.database import SessionLocal
from app.api.futures import (
    _get_raw_table_data,
    get_region_spot_prices_batch,
    get_spread_date_range,
)
from datetime import date, datetime

def main():
    db = SessionLocal()
    try:
        # 1. 检查分省区猪价 - 各省指标及观测数
        print("=" * 70)
        print("1. 分省区猪价 sheet 下各省份指标及观测数")
        print("=" * 70)
        from app.models.dim_metric import DimMetric
        from app.models.fact_observation import FactObservation
        from sqlalchemy import func

        regions = ["贵州", "四川", "云南", "广东", "广西", "江苏", "内蒙古", "内蒙", "中国", "全国"]
        for r in regions:
            m = db.query(DimMetric).filter(
                DimMetric.sheet_name == "分省区猪价",
                DimMetric.raw_header.like(f"%{r}%")
            ).first()
            if m:
                cnt = db.query(func.count(FactObservation.id)).filter(
                    FactObservation.metric_id == m.id,
                    FactObservation.period_type == "day",
                    FactObservation.value.isnot(None)
                ).scalar()
                rng = db.query(
                    func.min(FactObservation.obs_date),
                    func.max(FactObservation.obs_date)
                ).filter(
                    FactObservation.metric_id == m.id,
                    FactObservation.period_type == "day"
                ).first()
                print(f"  {r:8} id={m.id} raw_header={m.raw_header[:50]!r}... freq={m.freq} obs={cnt} date_range={rng[0]}~{rng[1]}")
            else:
                print(f"  {r:8} 未找到指标")

        # 2. 模拟 premium/v2 计算：贵州 03 合约，取若干日期
        print("\n" + "=" * 70)
        print("2. 模拟 premium/v2：贵州 + 03合约，抽样检查 premium 与 premium_ratio")
        print("=" * 70)

        excel_data = _get_raw_table_data(db, "期货结算价(1月交割连续)_生猪", "4.1、生猪期货升贴水数据")
        if not excel_data or len(excel_data) < 4:
            print("  未找到期货Excel数据")
            return

        # 取 A 列日期、C 列 03 合约
        sample_dates = []
        for row_idx in range(3, min(50, len(excel_data))):
            row = excel_data[row_idx]
            if len(row) < 3:
                continue
            from app.api.futures import _parse_excel_date
            date_obj = _parse_excel_date(row[0])
            if date_obj:
                try:
                    fv = float(row[2]) / 1000.0  # 03 合约 C 列
                    sample_dates.append((date_obj, fv))
                except (ValueError, TypeError):
                    pass

        all_dates = [d[0] for d in sample_dates]
        spot_map = get_region_spot_prices_batch(db, all_dates, "贵州")

        print(f"  期货日期抽样: {len(sample_dates)} 条")
        print(f"  贵州现货价格命中: {len(spot_map)} 条 (在 {len(all_dates)} 个日期中)")
        if len(spot_map) == 0:
            print("  => 贵州现货价格全为空，导致 premium 和 premium_ratio 均为空")

        # 抽样打印几条
        has_premium = 0
        has_ratio = 0
        for (trade_date, fs), i in zip(sample_dates[:15], range(15)):
            sp = spot_map.get(trade_date)
            premium = (fs - sp) if (fs is not None and sp is not None) else None
            is_delivery = (trade_date.month == 3)  # 03 合约
            ratio = None
            if premium is not None and fs and fs > 0 and not is_delivery:
                ratio = (premium / fs) * 100
            if premium is not None:
                has_premium += 1
            if ratio is not None:
                has_ratio += 1
            sp_str = f"{sp:.2f}" if sp is not None else "None"
            prem_str = f"{premium:.2f}" if premium is not None else "None"
            rat_str = f"{ratio:.2f}%" if ratio is not None else "None"
            print(f"    {trade_date} fs={fs:.2f} sp={sp_str} premium={prem_str} premium_ratio={rat_str} delivery_month={is_delivery}")

        print(f"\n  抽样15条: 有 premium 的 {has_premium} 条, 有 premium_ratio 的 {has_ratio} 条")
        if has_premium > 0 and has_ratio == 0:
            print("  => 若有 premium 但 premium_ratio 全为空，通常是 delivery_month 或 futures_settle<=0")

    finally:
        db.close()

if __name__ == "__main__":
    main()
