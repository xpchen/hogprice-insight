"""
检查D4. 结构分析功能所需的指标是否已存在
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_cr20_metrics():
    """检查CR20集团出栏环比指标"""
    print("=" * 80)
    print("1. 检查CR20集团出栏环比指标")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"汇总"sheet中的CR20相关指标
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        print(f"\n找到 {len(metrics)} 个'汇总'sheet的指标:")
        for m in metrics:
            print(f"  - ID: {m.id}, 名称: {m.metric_name}, Key: {m.parse_json.get('metric_key') if m.parse_json else 'N/A'}")
        
        # 查找CR20相关的指标
        cr20_metrics = [m for m in metrics if 'CR20' in str(m.parse_json.get('metric_key', '')) or '20' in m.metric_name]
        if cr20_metrics:
            print(f"\n找到 {len(cr20_metrics)} 个CR20相关指标:")
            for m in cr20_metrics:
                print(f"  - ID: {m.id}, 名称: {m.metric_name}, Key: {m.parse_json.get('metric_key') if m.parse_json else 'N/A'}")
        else:
            print("\n未找到CR20相关指标，可能需要从'汇总'sheet中计算")
    finally:
        db.close()

def check_yongyi_monthly_output():
    """检查涌益月度出栏环比指标"""
    print("\n" + "=" * 80)
    print("2. 检查涌益月度出栏环比指标")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"月度-商品猪出栏量"sheet的指标
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name.like('%月度%商品猪%')
        ).all()
        
        if metrics:
            print(f"\n找到 {len(metrics)} 个相关指标:")
            for m in metrics:
                print(f"  - ID: {m.id}, Sheet: {m.sheet_name}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
        else:
            print("\n未找到相关指标，可能需要从raw_table中读取")
    finally:
        db.close()

def check_ganglian_monthly_output():
    """检查钢联月度出栏环比指标"""
    print("\n" + "=" * 80)
    print("3. 检查钢联月度出栏环比指标")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"月度数据"sheet中出栏相关的指标
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "月度数据",
            DimMetric.raw_header.like('%出栏%')
        ).all()
        
        if metrics:
            print(f"\n找到 {len(metrics)} 个相关指标:")
            for m in metrics:
                print(f"  - ID: {m.id}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
                
                # 检查是否有数据
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == m.id
                ).count()
                print(f"    数据条数: {count}")
        else:
            print("\n未找到相关指标")
        
        # 检查是否有"全国"、"规模场"、"中小散户"相关的指标
        print("\n查找'全国'、'规模场'、'中小散户'相关指标:")
        scale_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "月度数据",
            or_(
                DimMetric.raw_header.like('%全国%'),
                DimMetric.raw_header.like('%规模场%'),
                DimMetric.raw_header.like('%中小散%')
            )
        ).all()
        
        if scale_metrics:
            for m in scale_metrics:
                print(f"  - ID: {m.id}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
    finally:
        db.close()

def check_ministry_agriculture():
    """检查农业部数据"""
    print("\n" + "=" * 80)
    print("4. 检查农业部出栏环比指标")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        metrics = db.query(DimMetric).filter(
            or_(
                DimMetric.sheet_name.like('%农业%'),
                DimMetric.metric_name.like('%农业%'),
                DimMetric.raw_header.like('%农业%')
            )
        ).limit(10).all()
        
        if metrics:
            print(f"\n找到 {len(metrics)} 个相关指标:")
            for m in metrics:
                print(f"  - ID: {m.id}, Sheet: {m.sheet_name}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
        else:
            print("\n未找到农业部相关数据")
    finally:
        db.close()

def check_slaughter():
    """检查定点企业屠宰环比指标"""
    print("\n" + "=" * 80)
    print("5. 检查定点企业屠宰环比指标")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找屠宰相关的指标
        metrics = db.query(DimMetric).filter(
            DimMetric.raw_header.like('%屠宰%')
        ).limit(10).all()
        
        if metrics:
            print(f"\n找到 {len(metrics)} 个相关指标:")
            for m in metrics:
                print(f"  - ID: {m.id}, Sheet: {m.sheet_name}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
                
                # 检查是否有环比数据
                if '环比' in m.raw_header or '环比' in m.metric_name:
                    count = db.query(FactObservation).filter(
                        FactObservation.metric_id == m.id
                    ).count()
                    print(f"    数据条数: {count}")
    finally:
        db.close()

if __name__ == "__main__":
    print("开始检查D4. 结构分析功能所需的指标...")
    
    check_cr20_metrics()
    check_yongyi_monthly_output()
    check_ganglian_monthly_output()
    check_ministry_agriculture()
    check_slaughter()
    
    print("\n检查完成！")
