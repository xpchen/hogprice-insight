"""
检查涌益咨询日度数据：sheet【各省份均价】的数据是否已导入数据库
"""
import sys
import io
from pathlib import Path

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.core.database import get_db
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def check_yongyi_province_avg():
    """检查各省份均价数据"""
    db: Session = next(get_db())
    
    try:
        print("=" * 80)
        print("检查涌益咨询日度数据：sheet【各省份均价】")
        print("=" * 80)
        
        # 1. 检查表是否存在
        print("\n1. 检查表 yongyi_daily_province_avg 是否存在...")
        result = db.execute(text("SHOW TABLES LIKE 'yongyi_daily_province_avg'"))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("   [X] 表 yongyi_daily_province_avg 不存在！")
            return
        
        print("   [OK] 表 yongyi_daily_province_avg 存在")
        
        # 2. 检查表中的数据量
        print("\n2. 检查表中的数据量...")
        result = db.execute(text("SELECT COUNT(*) as cnt FROM yongyi_daily_province_avg"))
        total_count = result.fetchone()[0]
        print(f"   总记录数: {total_count}")
        
        if total_count == 0:
            print("   [WARNING] 表中没有数据！")
            return
        
        # 3. 检查日期范围
        print("\n3. 检查日期范围...")
        result = db.execute(text("""
            SELECT 
                MIN(trade_date) as min_date,
                MAX(trade_date) as max_date,
                COUNT(DISTINCT trade_date) as date_count
            FROM yongyi_daily_province_avg
        """))
        row = result.fetchone()
        print(f"   最早日期: {row[0]}")
        print(f"   最新日期: {row[1]}")
        print(f"   不重复日期数: {row[2]}")
        
        # 4. 检查省份数量
        print("\n4. 检查省份数量...")
        result = db.execute(text("""
            SELECT 
                COUNT(DISTINCT region_code) as province_count,
                GROUP_CONCAT(DISTINCT region_code ORDER BY region_code SEPARATOR ', ') as provinces
            FROM yongyi_daily_province_avg
        """))
        row = result.fetchone()
        print(f"   不重复省份数: {row[0]}")
        print(f"   省份列表: {row[1]}")
        
        # 5. 检查每个省份的数据量
        print("\n5. 检查每个省份的数据量（前20个）...")
        result = db.execute(text("""
            SELECT 
                region_code,
                COUNT(*) as record_count,
                MIN(trade_date) as min_date,
                MAX(trade_date) as max_date
            FROM yongyi_daily_province_avg
            GROUP BY region_code
            ORDER BY record_count DESC
            LIMIT 20
        """))
        print("   省份\t\t记录数\t最早日期\t\t最新日期")
        print("   " + "-" * 60)
        for row in result:
            print(f"   {row[0]:<10}\t{row[1]:<8}\t{row[2]}\t{row[3]}")
        
        # 6. 检查是否已导入到 fact_observation 表
        print("\n6. 检查是否已导入到 fact_observation 表...")
        
        # 查找对应的metric
        metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "各省份均价",
            DimMetric.metric_name.like("%商品猪出栏均价%")
        ).first()
        
        if metric:
            print(f"   [OK] 找到metric: {metric.metric_name} (ID: {metric.id})")
            
            # 检查fact_observation中的数据
            obs_count = db.query(FactObservation).filter(
                FactObservation.metric_id == metric.id
            ).count()
            
            print(f"   fact_observation表中的记录数: {obs_count}")
            
            if obs_count > 0:
                # 检查日期范围
                result = db.execute(text("""
                    SELECT 
                        MIN(obs_date) as min_date,
                        MAX(obs_date) as max_date,
                        COUNT(DISTINCT obs_date) as date_count,
                        COUNT(DISTINCT geo_id) as geo_count
                    FROM fact_observation
                    WHERE metric_id = :metric_id
                """), {"metric_id": metric.id})
                
                row = result.fetchone()
                print(f"   最早日期: {row[0]}")
                print(f"   最新日期: {row[1]}")
                print(f"   不重复日期数: {row[2]}")
                print(f"   不重复省份数: {row[3]}")
            else:
                print("   [WARNING] fact_observation表中没有数据！")
        else:
            print("   [WARNING] 未找到对应的metric！")
            print("   尝试查找所有包含'各省份均价'的metric...")
            metrics = db.query(DimMetric).filter(
                DimMetric.sheet_name == "各省份均价"
            ).all()
            if metrics:
                print(f"   找到 {len(metrics)} 个metric:")
                for m in metrics:
                    print(f"     - {m.metric_name} (ID: {m.id}, raw_header: {m.raw_header})")
            else:
                print("   未找到任何metric！")
        
        # 7. 检查最近的数据
        print("\n7. 检查最近的数据（最近5条）...")
        result = db.execute(text("""
            SELECT trade_date, region_code, avg_price, updated_at
            FROM yongyi_daily_province_avg
            ORDER BY trade_date DESC, region_code
            LIMIT 5
        """))
        print("   日期\t\t省份\t\t均价\t\t更新时间")
        print("   " + "-" * 70)
        for row in result:
            print(f"   {row[0]}\t{row[1]:<10}\t{row[2]}\t{row[3]}")
        
        print("\n" + "=" * 80)
        print("检查完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] 检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_yongyi_province_avg()
