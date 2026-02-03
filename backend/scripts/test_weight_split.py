#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试周度-体重拆分"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.test_yongyi_weekly_import import main

if __name__ == "__main__":
    # 设置命令行参数
    sheet_name = "周度-体重拆分"
    sys.argv = [__file__, sheet_name]
    main()
