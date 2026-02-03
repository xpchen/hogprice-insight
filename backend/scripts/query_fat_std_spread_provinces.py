"""查询肥标价差数据中包含哪些省份"""
import sys
import os
import io
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from sqlalchemy import text, func, distinct
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.dim_region import DimRegion


def query_provinces_from_fact_observation(db):
    """从fact_observation表查询省份"""
    print("\n" + "="*80)
    print("从 fact_observation 表查询省份")
    print("="*80)
    
    # 查询"肥标价差"sheet的所有指标
    metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "肥标价差"
    ).all()
    
    if not metrics:
        print("  ❌ 未找到'肥标价差'相关的指标")
        return
    
    print(f"\n  找到 {len(metrics)} 个指标")
    
    # 查询每个指标对应的省份
    province_stats = {}
    
    for metric in metrics:
        # 从raw_header中提取省区名称
        import re
        raw_header = metric.raw_header
        province_name = None
        
        match = re.search(r'：([^：（）]+)（', raw_header)
        if match:
            province_name = match.group(1).strip()
        else:
            # 尝试查找省份列表
            provinces_list = ["四川", "贵州", "重庆", "湖南", "江西", "湖北", "河北", "河南", 
                             "山东", "山西", "辽宁", "吉林", "黑龙江", "中国"]
            for p in provinces_list:
                if p in raw_header:
                    province_name = p
                    break
        
        if not province_name:
            continue
        
        # 查询该指标的数据条数
        count = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id
        ).count()
        
        if count > 0:
            # 查询最新日期
            latest_obs = db.query(FactObservation).filter(
                FactObservation.metric_id == metric.id
            ).order_by(FactObservation.obs_date.desc()).first()
            
            latest_date = latest_obs.obs_date if latest_obs else None
            latest_value = float(latest_obs.value) if latest_obs and latest_obs.value else None
            
            province_stats[province_name] = {
                "count": count,
                "latest_date": latest_date,
                "latest_value": latest_value,
                "metric_id": metric.id,
                "raw_header": raw_header
            }
    
    # 显示结果
    if province_stats:
        print(f"\n  找到 {len(province_stats)} 个省份的数据：\n")
        print(f"  {'省份':<10} {'数据条数':<12} {'最新日期':<12} {'最新值':<12} {'指标ID':<10}")
        print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")
        
        # 按省份名称排序
        for province_name in sorted(province_stats.keys()):
            stats = province_stats[province_name]
            latest_date_str = stats["latest_date"].isoformat() if stats["latest_date"] else "N/A"
            latest_value_str = f"{stats['latest_value']:.2f}" if stats["latest_value"] is not None else "N/A"
            print(f"  {province_name:<10} {stats['count']:<12} {latest_date_str:<12} {latest_value_str:<12} {stats['metric_id']:<10}")
    else:
        print("  ⚠️  没有找到任何省份的数据")
    
    # 查询tags中的province信息
    print(f"\n  从tags_json中查询province字段：")
    try:
        # MySQL JSON查询
        results = db.execute(text("""
            SELECT DISTINCT
                JSON_UNQUOTE(JSON_EXTRACT(tags_json, '$.province')) as province,
                COUNT(*) as count,
                MAX(obs_date) as latest_date
            FROM fact_observation fo
            INNER JOIN dim_metric dm ON fo.metric_id = dm.id
            WHERE dm.sheet_name = '肥标价差'
                AND JSON_EXTRACT(tags_json, '$.province') IS NOT NULL
            GROUP BY province
            ORDER BY province
        """))
        
        print(f"\n  {'省份':<10} {'数据条数':<12} {'最新日期':<12}")
        print(f"  {'-'*10} {'-'*12} {'-'*12}")
        
        found_any = False
        for row in results:
            province = row[0]
            count = row[1]
            latest_date = row[2]
            if province:
                print(f"  {province:<10} {count:<12} {latest_date:<12}")
                found_any = True
        
        if not found_any:
            print("  ⚠️  没有找到tags_json中的province字段")
    except Exception as e:
        print(f"  ❌ 查询tags_json失败: {e}")


def query_provinces_from_table(db):
    """从ganglian_daily_fat_std_spread表查询省份"""
    print("\n" + "="*80)
    print("从 ganglian_daily_fat_std_spread 表查询省份")
    print("="*80)
    
    try:
        # 检查表是否存在
        from sqlalchemy import inspect as sql_inspect
        inspector = sql_inspect(db.bind)
        table_names = inspector.get_table_names()
        
        if "ganglian_daily_fat_std_spread" not in table_names:
            print("  ⚠️  表 ganglian_daily_fat_std_spread 不存在")
            return
        
        # 查询所有不同的省份
        results = db.execute(text("""
            SELECT 
                region_code,
                COUNT(*) as count,
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date,
                AVG(value) as avg_value
            FROM ganglian_daily_fat_std_spread
            GROUP BY region_code
            ORDER BY region_code
        """))
        
        print(f"\n  {'省份':<10} {'数据条数':<12} {'最早日期':<12} {'最新日期':<12} {'平均值':<12}")
        print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
        
        found_any = False
        for row in results:
            region_code = row[0]
            count = row[1]
            earliest_date = row[2]
            latest_date = row[3]
            avg_value = row[4]
            
            if region_code:
                avg_str = f"{avg_value:.2f}" if avg_value is not None else "N/A"
                print(f"  {region_code:<10} {count:<12} {earliest_date:<12} {latest_date:<12} {avg_str:<12}")
                found_any = True
        
        if not found_any:
            print("  ⚠️  表中没有数据")
            
    except Exception as e:
        print(f"  ❌ 查询表失败: {e}")
        import traceback
        traceback.print_exc()


def query_by_dim_metric(db):
    """通过dim_metric表查询所有省份"""
    print("\n" + "="*80)
    print("从 dim_metric 表查询所有省份（基于raw_header）")
    print("="*80)
    
    metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "肥标价差"
    ).all()
    
    if not metrics:
        print("  ❌ 未找到'肥标价差'相关的指标")
        return
    
    print(f"\n  找到 {len(metrics)} 个指标：\n")
    print(f"  {'省份':<10} {'指标ID':<10} {'指标名称':<20} {'原始列名':<40}")
    print(f"  {'-'*10} {'-'*10} {'-'*20} {'-'*40}")
    
    import re
    provinces_list = ["四川", "贵州", "重庆", "湖南", "江西", "湖北", "河北", "河南", 
                     "山东", "山西", "辽宁", "吉林", "黑龙江", "中国"]
    
    for metric in metrics:
        raw_header = metric.raw_header
        province_name = None
        
        match = re.search(r'：([^：（）]+)（', raw_header)
        if match:
            province_name = match.group(1).strip()
        else:
            for p in provinces_list:
                if p in raw_header:
                    province_name = p
                    break
        
        if not province_name:
            province_name = "未知"
        
        # 截断显示
        raw_header_display = raw_header[:38] + ".." if len(raw_header) > 40 else raw_header
        
        print(f"  {province_name:<10} {metric.id:<10} {metric.metric_name:<20} {raw_header_display:<40}")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("查询肥标价差数据中的省份")
    print("="*80)
    
    db = SessionLocal()
    try:
        # 方法1：从dim_metric表查询所有指标（显示所有可能的省份）
        query_by_dim_metric(db)
        
        # 方法2：从fact_observation表查询实际有数据的省份
        query_provinces_from_fact_observation(db)
        
        # 方法3：从独立表查询（如果存在）
        query_provinces_from_table(db)
        
        print("\n" + "="*80)
        print("查询完成")
        print("="*80)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
