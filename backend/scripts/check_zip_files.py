"""检查zip文件中的Excel文件"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

script_dir = Path(__file__).parent.parent
zip_path = script_dir.parent / "docs" / "生猪" / "数据库模板02：集团企业.zip"

if zip_path.exists():
    print(f"检查zip文件: {zip_path}")
    with zipfile.ZipFile(zip_path, 'r') as z:
        files = z.namelist()
        print(f"\n找到 {len(files)} 个文件:")
        for f in files:
            print(f"  - {f}")
            if f.endswith('.xlsx'):
                print(f"    ✓ Excel文件")
else:
    print(f"zip文件不存在: {zip_path}")
