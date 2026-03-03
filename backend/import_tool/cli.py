"""
统一数据导入工具 CLI 入口

用法:
    python -m import_tool init-db                          # 初始化数据库
    python -m import_tool bulk   --source-dir <DIR>        # 全量导入
    python -m import_tool incremental --source-dir <DIR>   # 增量导入
    python -m import_tool bulk --files "涌益咨询日度数据.xlsx"  # 指定文件
"""
import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

from sqlalchemy import text

from import_tool.db import (
    get_engine,
    init_db,
    populate_dim_region,
    truncate_fact_tables,
)
from import_tool.readers.r01_ganglian_daily import GanglianDailyReader
from import_tool.readers.r02_industry_data import IndustryDataReader
from import_tool.readers.r03_enterprise_province import EnterpriseProvinceReader
from import_tool.readers.r04_enterprise_monthly import EnterpriseMonthlyReader
from import_tool.readers.r05_carcass_market import CarcassMarketReader
from import_tool.readers.r06_futures_premium import FuturesPremiumReader
from import_tool.readers.r07_futures_basis import FuturesBasisReader
from import_tool.readers.r08_yongyi_daily import YongyiDailyReader
from import_tool.readers.r09_yongyi_weekly import YongyiWeeklyReader

# ── 文件 → Reader 映射 ──
# 顺序决定导入优先级
FILE_READERS = [
    ("涌益咨询日度数据.xlsx", YongyiDailyReader),
    ("涌益咨询 周度数据.xlsx", YongyiWeeklyReader),
    ("1、价格：钢联自动更新模板.xlsx", GanglianDailyReader),
    ("2、【生猪产业数据】.xlsx", IndustryDataReader),
    ("3.1、集团企业出栏跟踪【分省区】.xlsx", EnterpriseProvinceReader),
    ("3.2、集团企业月度数据跟踪.xlsx", EnterpriseMonthlyReader),
    ("3.3、白条市场跟踪.xlsx", CarcassMarketReader),
    ("4.1、生猪期货升贴水数据（盘面结算价）.xlsx", FuturesPremiumReader),
    ("4、生猪基差和月间价差研究.xlsx", FuturesBasisReader),
]

# 增量导入只处理这些文件（日度/周度更新频率高的）
INCREMENTAL_FILES = {
    "涌益咨询日度数据.xlsx",
    "涌益咨询 周度数据.xlsx",
    "1、价格：钢联自动更新模板.xlsx",
    "3.1、集团企业出栏跟踪【分省区】.xlsx",
    "3.3、白条市场跟踪.xlsx",
}


def find_file(source_dir: str, filename: str) -> str | None:
    """在 source_dir 及其子目录中查找文件。若存在多份同名文件（如钢联模板），
    优先选择路径中含 0226 或 生猪 的完整版（含仓单数据等 sheet）。"""
    candidates = []
    for root, dirs, files in os.walk(source_dir):
        for f in files:
            if f == filename:
                path = os.path.join(root, f)
                candidates.append(path)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # 多份同名：优先含 0226 / 生猪 的路径（完整钢联模板通常在该类目录下）
    for path in candidates:
        if "0226" in path or "生猪" in path:
            return path
    return candidates[0]


def file_hash(filepath: str) -> str:
    """计算文件 SHA256"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def create_batch(engine, filename: str, mode: str) -> int:
    """创建 import_batch 记录，返回 batch_id"""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "INSERT INTO import_batch (filename, mode, status) VALUES (:f, :m, 'processing')"
            ),
            {"f": filename, "m": mode},
        )
        conn.commit()
        return result.lastrowid


def update_batch(engine, batch_id: int, status: str, row_count: int = 0, duration_ms: int = 0, error_msg: str = None):
    """更新 import_batch 状态"""
    with engine.connect() as conn:
        conn.execute(
            text(
                "UPDATE import_batch SET status=:s, row_count=:r, duration_ms=:d, error_msg=:e WHERE id=:id"
            ),
            {"s": status, "r": row_count, "d": duration_ms, "e": error_msg, "id": batch_id},
        )
        conn.commit()


def run_bulk(engine, source_dir: str, file_filter: list[str] | None = None):
    """全量导入：TRUNCATE + INSERT"""
    print("=" * 60)
    print("  全量导入 (BULK)")
    print("=" * 60)

    # 1. 清空所有 fact 表
    truncate_fact_tables(engine)

    # 2. 填充维度表
    populate_dim_region(engine)

    total_rows = 0
    t0 = time.time()

    for filename, ReaderClass in FILE_READERS:
        # 文件过滤
        if file_filter and filename not in file_filter:
            continue

        filepath = find_file(source_dir, filename)
        if not filepath:
            print(f"  ⚠ 跳过: {filename} (未找到)")
            continue

        print(f"\n── {filename} ──")
        batch_id = create_batch(engine, filename, "bulk")
        t1 = time.time()

        try:
            reader = ReaderClass(engine, batch_id)
            results = reader.read_file(filepath)
            counts = reader.insert_all(results, mode="bulk")

            file_total = sum(counts.values())
            total_rows += file_total
            duration = int((time.time() - t1) * 1000)

            for table, n in counts.items():
                if n > 0:
                    print(f"    {table}: {n} 行")

            update_batch(engine, batch_id, "success", file_total, duration)
            print(f"  ✓ 完成 ({file_total} 行, {duration}ms)")

        except Exception as e:
            duration = int((time.time() - t1) * 1000)
            update_batch(engine, batch_id, "failed", 0, duration, str(e))
            print(f"  ✗ 失败: {e}")
            import traceback
            traceback.print_exc()

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  全量导入完成: {total_rows} 行, 耗时 {elapsed:.1f}s")
    print(f"{'=' * 60}")


def run_incremental(engine, source_dir: str, file_filter: list[str] | None = None):
    """增量导入：只 INSERT 新数据"""
    print("=" * 60)
    print("  增量导入 (INCREMENTAL)")
    print("=" * 60)

    total_new = 0
    t0 = time.time()

    for filename, ReaderClass in FILE_READERS:
        # 只处理增量文件
        if filename not in INCREMENTAL_FILES:
            continue
        if file_filter and filename not in file_filter:
            continue

        filepath = find_file(source_dir, filename)
        if not filepath:
            print(f"  ⚠ 跳过: {filename} (未找到)")
            continue

        print(f"\n── {filename} ──")
        batch_id = create_batch(engine, filename, "incremental")
        t1 = time.time()

        try:
            reader = ReaderClass(engine, batch_id)
            results = reader.read_file(filepath)
            counts = reader.insert_all(results, mode="incremental")

            file_total = sum(counts.values())
            total_new += file_total
            duration = int((time.time() - t1) * 1000)

            for table, n in counts.items():
                if n > 0:
                    print(f"    {table}: {n} 行 (新增)")

            update_batch(engine, batch_id, "success", file_total, duration)
            print(f"  ✓ 完成 ({file_total} 行新增, {duration}ms)")

        except Exception as e:
            duration = int((time.time() - t1) * 1000)
            update_batch(engine, batch_id, "failed", 0, duration, str(e))
            print(f"  ✗ 失败: {e}")
            import traceback
            traceback.print_exc()

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  增量导入完成: {total_new} 行新增, 耗时 {elapsed:.1f}s")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="HogPrice 统一数据导入工具")
    parser.add_argument(
        "command",
        choices=["init-db", "bulk", "incremental"],
        help="init-db: 初始化数据库 | bulk: 全量导入 | incremental: 增量导入",
    )
    parser.add_argument(
        "--source-dir",
        default="/Volumes/DEV/workspace/hogprice-insight/docs/生猪 2/",
        help="数据源目录",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="指定要导入的文件名（默认全部）",
    )

    args = parser.parse_args()
    engine = get_engine()

    if args.command == "init-db":
        init_db(engine)
        populate_dim_region(engine)
        # 初始化管理员用户
        with engine.connect() as conn:
            conn.execute(text(
                "INSERT IGNORE INTO sys_user (username, password_hash, is_active) "
                "VALUES ('admin', '$2b$12$LJ3m4ys3FMYq/QLHQHG8/upBkX.0rYJGjEBdQFOIHEKYwPBJJQJq', 1)"
            ))
            conn.execute(text("INSERT IGNORE INTO sys_role (role_name) VALUES ('admin'), ('analyst'), ('viewer')"))
            conn.commit()
        print("✓ 已初始化管理员用户和角色")
        return

    if args.command == "bulk":
        run_bulk(engine, args.source_dir, args.files)
    elif args.command == "incremental":
        run_incremental(engine, args.source_dir, args.files)


if __name__ == "__main__":
    main()
