"""
测试API端点
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import requests
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_api():
    """测试API"""
    print("=" * 80)
    print("测试白条市场API端点")
    print("=" * 80)
    
    try:
        url = "http://localhost:8000/api/v1/group-price/white-strip-market"
        params = {"days": 15}
        
        print(f"\n请求URL: {url}")
        print(f"参数: {params}")
        
        response = requests.get(url, params=params)
        
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n返回数据:")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            
            print(f"\n数据统计:")
            print(f"  数据条数: {len(data.get('data', []))}")
            print(f"  市场列表: {data.get('markets', [])}")
            print(f"  最新日期: {data.get('latest_date')}")
            
            if data.get('data'):
                print(f"\n前5条数据:")
                for item in data['data'][:5]:
                    print(f"  {item}")
        else:
            print(f"\n错误: {response.text}")
            
    except Exception as e:
        print(f"\n异常: {e}")

if __name__ == "__main__":
    test_api()
