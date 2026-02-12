# -*- coding: utf-8 -*-
"""
查询近15天华宝白条、牧原白条及华东等区域在 fact_observation 中的指标与数据
"""
import sys
import io
from pathlib import Path
from datetime import date, timedelta

if sys.stdout.encoding and sys.stdout.encoding.upper() != 'UTF-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
script_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(script_dir))

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation


def main():
    db: Session = SessionLocal()
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=15)
        print(f"查询时间范围: {start_date} ~ {end_date} (近15天)\n")

        # 1. 华宝和牧原白条 sheet 下所有指标
        metrics = (
            db.query(DimMetric)
            .filter(DimMetric.sheet_name == "华宝和牧原白条")
            .all()
        )
        print(f"【华宝和牧原白条】sheet 指标数: {len(metrics)}")
        for m in metrics:
            pk = m.parse_json.get("metric_key") if m.parse_json else None
            print(f"  id={m.id}  metric_key={pk}  metric_name={m.metric_name}  raw_header={m.raw_header!r}")
        print()

        # 2. 华宝白条：按 metric_key 或 华宝
        huabao = (
            db.query(DimMetric)
            .filter(
                DimMetric.sheet_name == "华宝和牧原白条",
                func.json_unquote(func.json_extract(DimMetric.parse_json, "$.metric_key")) == "WHITE_STRIP_PRICE_HUABAO",
            )
            .first()
        )
        if not huabao:
            huabao_list = (
                db.query(DimMetric)
                .filter(
                    DimMetric.sheet_name == "华宝和牧原白条",
                    DimMetric.raw_header.like("%华宝%"),
                )
                .all()
            )
            huabao = huabao_list[0] if huabao_list else None
        if huabao:
            obs = (
                db.query(FactObservation.obs_date, FactObservation.value)
                .filter(
                    FactObservation.metric_id == huabao.id,
                    FactObservation.obs_date >= start_date,
                    FactObservation.obs_date <= end_date,
                )
                .order_by(desc(FactObservation.obs_date))
                .all()
            )
            print(f"【华宝白条】metric_id={huabao.id}  raw_header={huabao.raw_header!r}  近15天观测数: {len(obs)}")
            for o in obs[:20]:
                print(f"  {o.obs_date}  value={o.value}")
            if len(obs) > 20:
                print(f"  ... 共 {len(obs)} 条")
        else:
            print("【华宝白条】未找到对应指标")
        print()

        # 3. 牧原白条：按 metric_key 或 牧原
        muyuan = (
            db.query(DimMetric)
            .filter(
                DimMetric.sheet_name == "华宝和牧原白条",
                func.json_unquote(func.json_extract(DimMetric.parse_json, "$.metric_key")) == "WHITE_STRIP_PRICE_MUYUAN",
            )
            .first()
        )
        if not muyuan:
            muyuan_list = (
                db.query(DimMetric)
                .filter(
                    DimMetric.sheet_name == "华宝和牧原白条",
                    DimMetric.raw_header.like("%牧原%"),
                )
                .all()
            )
            muyuan = muyuan_list[0] if muyuan_list else None
        if muyuan:
            obs = (
                db.query(FactObservation.obs_date, FactObservation.value)
                .filter(
                    FactObservation.metric_id == muyuan.id,
                    FactObservation.obs_date >= start_date,
                    FactObservation.obs_date <= end_date,
                )
                .order_by(desc(FactObservation.obs_date))
                .all()
            )
            print(f"【牧原白条】metric_id={muyuan.id}  raw_header={muyuan.raw_header!r}  近15天观测数: {len(obs)}")
            for o in obs[:20]:
                print(f"  {o.obs_date}  value={o.value}")
            if len(obs) > 20:
                print(f"  ... 共 {len(obs)} 条")
        else:
            print("【牧原白条】未找到对应指标")
        print()

        # 4. 华东、河南山东、湖北陕西、京津冀、东北
        region_keys = [
            ("华东", "WHITE_STRIP_PRICE_EAST_CHINA"),
            ("河南山东", "WHITE_STRIP_PRICE_HENAN_SHANDONG"),
            ("湖北陕西", "WHITE_STRIP_PRICE_HUBEI_SHANXI"),
            ("京津冀", "WHITE_STRIP_PRICE_JINGJINJI"),
            ("东北", "WHITE_STRIP_PRICE_NORTHEAST"),
        ]
        for name, key in region_keys:
            m = (
                db.query(DimMetric)
                .filter(
                    DimMetric.sheet_name == "华宝和牧原白条",
                    func.json_unquote(func.json_extract(DimMetric.parse_json, "$.metric_key")) == key,
                )
                .first()
            )
            if not m:
                m = (
                    db.query(DimMetric)
                    .filter(
                        DimMetric.sheet_name == "华宝和牧原白条",
                        DimMetric.raw_header.like(f"%{name}%"),
                    )
                    .first()
                )
            if m:
                cnt = (
                    db.query(func.count(FactObservation.id))
                    .filter(
                        FactObservation.metric_id == m.id,
                        FactObservation.obs_date >= start_date,
                        FactObservation.obs_date <= end_date,
                    )
                    .scalar()
                )
                print(f"【{name}】metric_id={m.id}  近15天观测数: {cnt}")
            else:
                print(f"【{name}】未找到对应指标")
    finally:
        db.close()


if __name__ == "__main__":
    main()
