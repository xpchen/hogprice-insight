"""
检查数据库中的文件名
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.raw_sheet import RawSheet
from app.models.raw_file import RawFile

def check_file_names():
    """检查数据库中的文件名"""
    db: Session = SessionLocal()
    try:
        # 查找"集团企业全国"sheet
        enterprise_sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "集团企业全国"
        ).first()
        
        if enterprise_sheet:
            print(f"找到sheet: {enterprise_sheet.sheet_name}")
            print(f"文件ID: {enterprise_sheet.raw_file_id}")
            if enterprise_sheet.raw_file:
                print(f"文件名: {enterprise_sheet.raw_file.filename}")
                print(f"文件路径: {enterprise_sheet.raw_file.storage_path}")
        
        # 查找所有包含"集团企业"的文件
        print(f"\n所有包含'集团企业'的文件:")
        all_files = db.query(RawFile).filter(
            RawFile.filename.like('%集团企业%')
        ).all()
        for f in all_files:
            print(f"  - {f.filename}")
    finally:
        db.close()

if __name__ == "__main__":
    check_file_names()
