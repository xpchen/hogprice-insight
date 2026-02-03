"""
导入毛白价差sheet数据
直接调用test_ganglian_sheet_import.py的功能
"""
import sys
import os
from pathlib import Path

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 修改sys.argv来模拟命令行参数
original_argv = sys.argv.copy()
sys.argv = [sys.argv[0], '毛白价差', '-y']

# 导入并运行test_ganglian_sheet_import的main函数
from scripts.test_ganglian_sheet_import import main

if __name__ == "__main__":
    try:
        main()
    finally:
        sys.argv = original_argv
