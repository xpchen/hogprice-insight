"""
Check premium sheet in database
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.models.raw_sheet import RawSheet
from app.models.raw_file import RawFile
from sqlalchemy import or_

def check_sheets():
    """Check sheets in database"""
    db = SessionLocal()
    try:
        # Search for sheets containing "期货" or "升贴水" or "4.1"
        sheets = db.query(RawSheet).join(RawFile).filter(
            or_(
                RawSheet.sheet_name.like('%期货%'),
                RawSheet.sheet_name.like('%升贴水%'),
                RawFile.filename.like('%4.1%')
            )
        ).all()
        
        print(f"Found {len(sheets)} sheets:")
        for sheet in sheets:
            file = db.query(RawFile).filter(RawFile.id == sheet.raw_file_id).first()
            print(f"\n  Sheet: {sheet.sheet_name}")
            print(f"  File: {file.filename if file else 'N/A'}")
            print(f"  ID: {sheet.id}")
        
        # Also check for exact match
        exact_sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "期货结算价(1月交割连续)_生猪"
        ).first()
        
        if exact_sheet:
            file = db.query(RawFile).filter(RawFile.id == exact_sheet.raw_file_id).first()
            print(f"\n✅ Found exact match:")
            print(f"  Sheet: {exact_sheet.sheet_name}")
            print(f"  File: {file.filename if file else 'N/A'}")
        else:
            print("\n❌ Exact match not found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 80)
    print("Check Premium Sheet in Database")
    print("=" * 80)
    check_sheets()
