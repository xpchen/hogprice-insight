"""
分析D4. 结构分析功能的数据源结构
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import pandas as pd
import zipfile

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze_yongyi_monthly_output():
    """分析涌益月度-商品猪出栏量sheet"""
    print("=" * 80)
    print("1. 分析《涌益咨询 周度数据》的'月度-商品猪出栏量'sheet")
    print("=" * 80)
    
    docs_dir = script_dir.parent / "docs"
    yongyi_files = list(docs_dir.glob("*涌益咨询*周度数据*.xlsx"))
    
    if yongyi_files:
        file_path = yongyi_files[0]
        print(f"\n找到文件: {file_path.name}")
        
        try:
            df = pd.read_excel(file_path, sheet_name="月度-商品猪出栏量", header=None, engine='openpyxl')
            
            print(f"\nSheet形状: {df.shape}")
            print(f"\n前15行数据:")
            print(df.head(15).to_string())
            
            # B列和C列（索引1和2）
            print(f"\nB列（第2列，索引1）数据示例:")
            if df.shape[1] > 1:
                print(df.iloc[:, 1].head(20).tolist())
            
            print(f"\nC列（第3列，索引2）数据示例:")
            if df.shape[1] > 2:
                print(df.iloc[:, 2].head(20).tolist())
            
            return True
        except Exception as e:
            print(f"读取失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("未找到涌益周度数据文件")
        return False

def analyze_ganglian_monthly_output():
    """分析钢联月度出栏sheet"""
    print("\n" + "=" * 80)
    print("2. 分析《价格：钢联自动更新模板》的'月度出栏'sheet")
    print("=" * 80)
    
    docs_dir = script_dir.parent / "docs"
    ganglian_files = list(docs_dir.glob("*钢联自动更新模板*.xlsx"))
    
    if ganglian_files:
        file_path = ganglian_files[0]
        print(f"\n找到文件: {file_path.name}")
        
        try:
            # 先检查是否有"月度出栏"sheet
            excel_file = pd.ExcelFile(file_path, engine='openpyxl')
            sheet_names = excel_file.sheet_names
            print(f"\n所有sheet名称: {sheet_names}")
            
            # 查找包含"月度"或"出栏"的sheet
            monthly_sheets = [s for s in sheet_names if '月度' in s or '出栏' in s]
            print(f"\n包含'月度'或'出栏'的sheet: {monthly_sheets}")
            
            if "月度出栏" in sheet_names:
                df = pd.read_excel(file_path, sheet_name="月度出栏", header=None, engine='openpyxl')
                
                print(f"\nSheet形状: {df.shape}")
                print(f"\n前15行数据:")
                print(df.head(15).to_string())
                
                # 查找全国、规模场、中小散户的列
                print(f"\n查找'全国'、'规模场'、'中小散户'列:")
                if len(df) > 1:
                    header_row = df.iloc[1].tolist() if len(df) > 1 else []
                    print(f"第2行（表头）: {header_row[:20]}")
                    
                    # 查找包含这些关键词的列
                    for idx, val in enumerate(header_row):
                        if val and isinstance(val, str):
                            if '全国' in val or '规模场' in val or '中小散' in val or '中小散户' in val:
                                print(f"  列{idx}: {val}")
                                # 显示该列的数据示例
                                if len(df) > 2:
                                    col_data = df.iloc[2:10, idx].tolist()
                                    print(f"    数据示例: {col_data}")
            
            return True
        except Exception as e:
            print(f"读取失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("未找到钢联文件")
        return False

def analyze_ministry_agriculture():
    """分析农业部数据（需要先找到数据源）"""
    print("\n" + "=" * 80)
    print("3. 分析农业部数据")
    print("=" * 80)
    
    # 先检查数据库中是否有农业部相关的数据
    from sqlalchemy.orm import Session
    from sqlalchemy import or_
    from app.core.database import SessionLocal
    from app.models.dim_metric import DimMetric
    
    db: Session = SessionLocal()
    try:
        # 查找包含"农业部"或"农业"的指标
        metrics = db.query(DimMetric).filter(
            or_(
                DimMetric.sheet_name.like('%农业%'),
                DimMetric.metric_name.like('%农业%'),
                DimMetric.raw_header.like('%农业%')
            )
        ).limit(10).all()
        
        if metrics:
            print(f"找到 {len(metrics)} 个相关指标:")
            for m in metrics:
                print(f"  - Sheet: {m.sheet_name}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
        else:
            print("未找到农业部相关数据")
            print("可能需要从其他数据源导入")
    finally:
        db.close()

def analyze_slaughter_data():
    """分析定点企业屠宰数据"""
    print("\n" + "=" * 80)
    print("4. 分析定点企业屠宰数据")
    print("=" * 80)
    
    from sqlalchemy.orm import Session
    from sqlalchemy import or_
    from app.core.database import SessionLocal
    from app.models.dim_metric import DimMetric
    
    db: Session = SessionLocal()
    try:
        # 查找包含"屠宰"的指标
        metrics = db.query(DimMetric).filter(
            or_(
                DimMetric.sheet_name.like('%屠宰%'),
                DimMetric.metric_name.like('%屠宰%'),
                DimMetric.raw_header.like('%屠宰%')
            )
        ).limit(10).all()
        
        if metrics:
            print(f"找到 {len(metrics)} 个相关指标:")
            for m in metrics:
                print(f"  - Sheet: {m.sheet_name}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
        else:
            print("未找到屠宰相关数据")
    finally:
        db.close()

if __name__ == "__main__":
    print("开始分析D4. 结构分析功能的数据源...")
    
    analyze_yongyi_monthly_output()
    analyze_ganglian_monthly_output()
    analyze_ministry_agriculture()
    analyze_slaughter_data()
    
    print("\n分析完成！")
