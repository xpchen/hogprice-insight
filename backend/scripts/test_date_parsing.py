"""
测试日期解析逻辑
"""
# -*- coding: utf-8 -*-
import sys
import io
from datetime import datetime, date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def parse_date(date_val):
    """解析日期"""
    date_obj = None
    if isinstance(date_val, str):
        try:
            # 处理ISO格式：2025-03-01T00:00:00
            if 'T' in date_val:
                date_str = date_val.split('T')[0]
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                # 尝试多种日期格式
                date_str = date_val.split()[0] if ' ' in date_val else date_val
                # 尝试 YYYY-MM-DD
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    # 尝试 YYYY/M/D 或 YYYY/MM/DD
                    try:
                        date_obj = datetime.strptime(date_str, '%Y/%m/%d').date()
                    except:
                        # 尝试 YYYY/M/D（单数字月份和日期）
                        try:
                            parts = date_str.split('/')
                            if len(parts) == 3:
                                year = int(parts[0])
                                month = int(parts[1])
                                day = int(parts[2])
                                date_obj = date(year, month, day)
                        except:
                            pass
        except:
            pass
    elif isinstance(date_val, date):
        date_obj = date_val
    elif hasattr(date_val, 'date'):
        date_obj = date_val.date()
    
    return date_obj

# 测试各种日期格式
test_dates = [
    '2025-03-01T00:00:00',  # ISO格式
    '2025-03-01',  # 标准格式
    '2026/1/1',  # 单数字格式
    '2026/01/01',  # 标准斜杠格式
    '2026/12/31',  # 标准斜杠格式
    '2025-03-01 00:00:00',  # 带时间的格式
]

print("测试日期解析:")
for test_date in test_dates:
    result = parse_date(test_date)
    print(f"  {test_date:30} -> {result}")
