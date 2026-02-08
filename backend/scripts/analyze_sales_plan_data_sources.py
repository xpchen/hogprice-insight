"""
分析D3. 销售计划功能的数据源结构
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

def analyze_enterprise_summary():
    """分析集团企业月度数据跟踪的汇总sheet"""
    print("=" * 80)
    print("1. 分析《集团企业月度数据跟踪》的'汇总'sheet")
    print("=" * 80)
    
    zip_path = script_dir.parent / "docs" / "生猪" / "数据库模板02：集团企业.zip"
    excel_filename = "3.2、集团企业月度数据跟踪.xlsx"
    
    if zip_path.exists():
        with zipfile.ZipFile(zip_path, 'r') as z:
            if excel_filename in z.namelist():
                with z.open(excel_filename) as f:
                    df = pd.read_excel(f, sheet_name="汇总", header=None, engine='openpyxl')
                    
                    print(f"\nSheet形状: {df.shape}")
                    print(f"\n前10行数据:")
                    print(df.head(10).to_string())
                    
                    print(f"\n列结构分析:")
                    # 第1行：地区分组
                    row1 = df.iloc[0].tolist() if len(df) > 0 else []
                    print(f"第1行（地区分组）: {row1[:20]}")
                    
                    # 第2行：指标名称
                    row2 = df.iloc[1].tolist() if len(df) > 1 else []
                    print(f"第2行（指标名称）: {row2[:20]}")
                    
                    # 第3行开始：数据
                    if len(df) > 2:
                        print(f"\n第3行数据示例:")
                        print(df.iloc[2].tolist()[:20])
                    
                    return True
    
    print("未找到文件")
    return False

def analyze_yongyi_monthly_plan():
    """分析涌益咨询周度数据的月度计划出栏量sheet"""
    print("\n" + "=" * 80)
    print("2. 分析《涌益咨询 周度数据》的'月度计划出栏量'sheet")
    print("=" * 80)
    
    # 查找涌益周度数据文件
    docs_dir = script_dir.parent / "docs"
    yongyi_files = list(docs_dir.glob("*涌益咨询*周度数据*.xlsx"))
    
    if yongyi_files:
        file_path = yongyi_files[0]
        print(f"\n找到文件: {file_path.name}")
        
        try:
            df = pd.read_excel(file_path, sheet_name="月度计划出栏量", header=None, engine='openpyxl')
            
            print(f"\nSheet形状: {df.shape}")
            print(f"\n前15行数据:")
            print(df.head(15).to_string())
            
            # 查找Q列和R列（第17列和第18列，索引16和17）
            print(f"\nQ列（第17列，索引16）数据示例:")
            if df.shape[1] > 16:
                print(df.iloc[:, 16].head(20).tolist())
            
            print(f"\nR列（第18列，索引17）数据示例:")
            if df.shape[1] > 17:
                print(df.iloc[:, 17].head(20).tolist())
            
            return True
        except Exception as e:
            print(f"读取失败: {e}")
            return False
    else:
        print("未找到涌益周度数据文件")
        return False

def analyze_ganglian_monthly():
    """分析钢联自动更新模板的月度数据sheet"""
    print("\n" + "=" * 80)
    print("3. 分析《价格：钢联自动更新模板》的'月度数据'sheet")
    print("=" * 80)
    
    # 查找钢联文件
    docs_dir = script_dir.parent / "docs"
    ganglian_files = list(docs_dir.glob("*钢联自动更新模板*.xlsx"))
    
    if ganglian_files:
        file_path = ganglian_files[0]
        print(f"\n找到文件: {file_path.name}")
        
        try:
            df = pd.read_excel(file_path, sheet_name="月度数据", header=None, engine='openpyxl')
            
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
            return False
    else:
        print("未找到钢联文件")
        return False

if __name__ == "__main__":
    print("开始分析D3. 销售计划功能的数据源...")
    
    analyze_enterprise_summary()
    analyze_yongyi_monthly_plan()
    analyze_ganglian_monthly()
    
    print("\n分析完成！")
