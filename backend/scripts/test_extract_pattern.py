"""测试extract_pattern是否正确"""
import sys
import io
import re

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 测试正则表达式
pattern = "生猪标肥：价差：(.*?)（日）"
test_cases = [
    "生猪标肥：价差：中国（日）",
    "生猪标肥：价差：四川（日）",
    "生猪标肥：价差：湖南（日）",
    "生猪标肥：价差：河南（日）",
]

print("测试正则表达式:", pattern)
print("="*60)

for test in test_cases:
    match = re.search(pattern, test)
    if match:
        extracted = match.group(1)
        print(f"✓ {test:<30} -> {extracted}")
    else:
        print(f"✗ {test:<30} -> 未匹配")
