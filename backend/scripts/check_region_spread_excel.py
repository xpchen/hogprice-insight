# -*- coding: utf-8 -*-
"""检查区域价差Excel文件结构"""
import pandas as pd
from pathlib import Path
import sys
import io

# 设置UTF-8编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

workspace_root = Path(__file__).parent.parent.parent
file_path = workspace_root / "docs" / "1、价格：钢联自动更新模板.xlsx"

print(f"检查文件: {file_path}")
print(f"文件存在: {file_path.exists()}")

if not file_path.exists():
    print("文件不存在！")
    sys.exit(1)

excel_file = pd.ExcelFile(file_path, engine='openpyxl')
print(f"\nSheet列表: {excel_file.sheet_names}")
print(f"区域价差sheet存在: {'区域价差' in excel_file.sheet_names}")

if '区域价差' not in excel_file.sheet_names:
    print("区域价差sheet不存在！")
    sys.exit(1)

# 读取前几行
print("\n读取前15行数据:")
df = pd.read_excel(excel_file, sheet_name='区域价差', header=None, nrows=15)
print(df)

# 读取指标名称行（第2行，index=1）
print("\n读取指标名称行（第2行）:")
indicator_names_df = pd.read_excel(
    excel_file, sheet_name='区域价差',
    header=None, nrows=1, skiprows=1
)
indicator_names = indicator_names_df.iloc[0].tolist()
print(f"指标名称: {indicator_names}")

# 读取数据（从第5行开始）
print("\n读取数据行（从第5行开始，前5行）:")
df_data = pd.read_excel(
    excel_file, sheet_name='区域价差',
    header=None, skiprows=4, nrows=5
)
print(df_data)

# 检查第一列（日期列）的数据
print("\n第一列（日期列）前5个值:")
print(df_data.iloc[:5, 0])

# 检查第二列（第一个区域对）的数据
print("\n第二列（第一个区域对）前5个值:")
print(df_data.iloc[:5, 1])
