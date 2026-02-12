"""
Test Premium V2 API
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.api.futures import _get_raw_table_data, get_region_spot_price
from datetime import date

def test_read_excel_data():
    """Test reading Excel data"""
    db = SessionLocal()
    try:
        data = _get_raw_table_data(db, "期货结算价(1月交割连续)_生猪", "4.1")
        
        if not data:
            print("Not found data")
            return
        
        print(f"Found data, total {len(data)} rows")
        print(f"\nFirst 5 rows:")
        for i in range(min(5, len(data))):
            print(f"  Row {i}: {data[i]}")
        
        # Check data structure
        if len(data) >= 4:
            print(f"\nRow 1 (header): {data[0]}")
            print(f"Row 2 (unit): {data[1]}")
            print(f"Row 3 (source): {data[2]}")
            print(f"Row 4 (data): {data[3]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def test_region_spot_price():
    """Test region spot price"""
    db = SessionLocal()
    try:
        test_date = date(2024, 1, 15)
        regions = ["全国均价", "贵州", "四川", "云南", "广东", "广西", "江苏", "内蒙"]
        
        print("\nTest region spot price:")
        for region in regions:
            price = get_region_spot_price(db, test_date, region)
            if price:
                print(f"  {region}: {price} yuan/kg")
            else:
                print(f"  {region}: Not found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 80)
    print("Test Premium V2 API")
    print("=" * 80)
    
    test_read_excel_data()
    test_region_spot_price()
