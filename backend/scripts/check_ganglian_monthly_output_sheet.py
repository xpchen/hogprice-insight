"""
检查钢联"月度出栏"sheet的结构
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import json

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

def _get_raw_table_data(db: Session, sheet_name: str, filename_pattern: str = None):
    """获取raw_table数据"""
    query = db.query(RawSheet).join(RawFile)
    
    if filename_pattern:
        query = query.filter(RawFile.filename.like(f'%{filename_pattern}%'))
    
    sheet = query.filter(RawSheet.sheet_name == sheet_name).first()
    
    if not sheet:
        return None
    
    raw_table = db.query(RawTable).filter(
        RawTable.raw_sheet_id == sheet.id
    ).first()
    
    if not raw_table:
        return None
    
    table_data = raw_table.table_json
    if isinstance(table_data, str):
        table_data = json.loads(table_data)
    
    return table_data

def check_ganglian_monthly_output():
    """检查钢联月度出栏sheet结构"""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("检查钢联'月度出栏'sheet结构")
        print("=" * 80)
        
        monthly_output_data = _get_raw_table_data(db, "月度出栏", "钢联自动更新模板")
        
        if not monthly_output_data:
            print("未找到'月度出栏'sheet数据")
            return
        
        print(f"\n找到'月度出栏'数据，共{len(monthly_output_data)}行")
        
        # 显示前10行数据，查看表头结构
        print("\n前10行数据:")
        for i, row in enumerate(monthly_output_data[:10]):
            print(f"\n第{i+1}行（索引{i}）:")
            for j, cell in enumerate(row[:20]):  # 只显示前20列
                if cell is not None and cell != "":
                    col_letter = chr(ord('A') + j) if j < 26 else f"A{chr(ord('A') + j - 26)}"
                    print(f"  {col_letter}列（索引{j}）: {cell}")
        
        # 查找包含"全国"、"规模场"、"中小散户"、"出栏"的列
        print("\n\n查找包含'全国'、'规模场'、'中小散户'、'出栏'的列:")
        for i in range(min(3, len(monthly_output_data))):
            row = monthly_output_data[i]
            print(f"\n第{i+1}行:")
            for j, cell in enumerate(row):
                if cell and isinstance(cell, str):
                    if '全国' in cell or '规模场' in cell or '中小散' in cell or '出栏' in cell:
                        col_letter = chr(ord('A') + j) if j < 26 else f"A{chr(ord('A') + j - 26)}"
                        print(f"  {col_letter}列（索引{j}）: {cell}")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_ganglian_monthly_output()
