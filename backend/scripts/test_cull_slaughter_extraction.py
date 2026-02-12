"""
直接调用 multi_source 的提取逻辑，打印 cull_slaughter_data 的月份与数值，确认 2025 是否被算出。
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.api.multi_source import _extract_cull_slaughter_data


def main():
    db = SessionLocal()
    try:
        data = _extract_cull_slaughter_data(db)
        months = sorted(data.keys())
        print("cull_slaughter_data 月份数:", len(months))
        print("月份范围:", months[0] if months else "无", "~", months[-1] if months else "无")
        print("\n2024 年各月 涌益/钢联:")
        for m in months:
            if not m.startswith("2024"):
                continue
            v = data[m]
            print(f"  {m}: 涌益={v.get('cull_slaughter_yongyi')}, 钢联={v.get('cull_slaughter_ganglian')}")
        print("\n2025 年各月 涌益/钢联:")
        for m in months:
            if not m.startswith("2025"):
                continue
            v = data[m]
            print(f"  {m}: 涌益={v.get('cull_slaughter_yongyi')}, 钢联={v.get('cull_slaughter_ganglian')}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
