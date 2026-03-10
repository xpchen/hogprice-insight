#!/usr/bin/env python3
"""
一键数据导入 + 缓存刷新脚本

用法:
    python import_data.py                                    # 使用默认目录增量导入
    python import_data.py /path/to/data                      # 指定数据目录
    python import_data.py --mode bulk                        # 全量导入（TRUNCATE + INSERT）
    python import_data.py --files "涌益咨询日度数据.xlsx"      # 只导入指定文件
"""
import argparse
import os
import sys
import time

# 将 backend 加入 path，以便复用 import_tool 和 app 模块
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import text

from import_tool.db import get_engine
from import_tool.cli import (
    FILE_READERS,
    find_file,
    create_batch,
    update_batch,
    run_bulk,
)

# ── 默认数据目录 ──
DEFAULT_SOURCE_DIR = "/Volumes/DEV/workspace/hogprice-insight/docs/生猪 2/"

# ── 需要清除缓存的 API 前缀（覆盖 dashboard / price / slaughter 页） ──
CACHE_PREFIXES_TO_CLEAR = [
    "/api/v1/price-display/national-price",
    "/api/v1/price-display/fat-std-spread",
    "/api/v1/price-display/price-and-spread",
    "/api/v1/price-display/price-changes",
    "/api/v1/price-display/slaughter",
    "/api/v1/price-display/slaughter-price-trend",
    "/api/v1/price-display/region-spread",
    "/api/v1/price-display/industry-chain",
    "/api/v1/price-display/province-indicators",
    "/api/v1/price-display/frozen-inventory",
    "/api/v1/price-display/live-white-spread",
    "/api/v1/multi-source",
    "/api/v1/supply-demand",
    "/api/v1/structure-analysis",
    "/api/v1/statistics-bureau",
    "/api/v1/observation",
    "/api/futures/premium",
    "/api/futures/volatility",
    "/api/futures/calendar-spread",
]

# 预热由后端内部 API 完成，URL 列表见 backend/app/core/quick_chart_config.py QUICK_CHART_PRECOMPUTE_URLS

BASE_URL = "http://127.0.0.1:8000"


def print_header(title: str, subtitle: str = ""):
    print()
    print("=" * 60)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print("=" * 60)


def print_separator():
    print("─" * 60)


def run_incremental_import(engine, source_dir: str, file_filter: list[str] | None = None):
    """增量导入：遍历所有 FILE_READERS，INSERT 新数据"""
    total_new = 0
    total_files = 0
    skipped_files = 0
    t0 = time.time()

    readers_to_run = [
        (fn, rc) for fn, rc in FILE_READERS
        if not file_filter or fn in file_filter
    ]

    for idx, (filename, ReaderClass) in enumerate(readers_to_run, 1):
        filepath = find_file(source_dir, filename)
        if not filepath:
            print(f"\n  [{idx}/{len(readers_to_run)}] {filename}")
            print(f"      ⚠ 跳过 (未找到)")
            skipped_files += 1
            continue

        print(f"\n  [{idx}/{len(readers_to_run)}] {filename}")
        batch_id = create_batch(engine, filename, "incremental")
        t1 = time.time()

        try:
            reader = ReaderClass(engine, batch_id)
            results = reader.read_file(filepath)
            counts = reader.insert_all(results, mode="incremental")

            file_total = sum(counts.values())
            total_new += file_total
            total_files += 1
            duration = time.time() - t1

            for table, n in counts.items():
                if n > 0:
                    print(f"      → {table}: {n} 行")

            update_batch(engine, batch_id, "success", file_total, int(duration * 1000))
            print(f"      ✓ 完成 ({file_total} 行新增, {duration:.1f}s)")

        except Exception as e:
            duration = time.time() - t1
            update_batch(engine, batch_id, "failed", 0, int(duration * 1000), str(e))
            print(f"      ✗ 失败: {e}")
            import traceback
            traceback.print_exc()

    elapsed = time.time() - t0
    print_separator()
    print(f"  导入汇总: {total_files} 个文件处理, {skipped_files} 个跳过, "
          f"{total_new:,} 行新增, 耗时 {elapsed:.1f}s")
    print_separator()
    return total_new


def clear_cache(engine):
    """按前缀删除相关 API 的缓存"""
    print("\n  清除缓存...")
    total_cleared = 0

    with engine.connect() as conn:
        for prefix in CACHE_PREFIXES_TO_CLEAR:
            result = conn.execute(
                text("DELETE FROM quick_chart_cache WHERE cache_key LIKE :pattern"),
                {"pattern": f"{prefix}%"},
            )
            n = result.rowcount
            if n > 0:
                print(f"    {prefix}: {n} 条")
                total_cleared += n
        conn.commit()

    if total_cleared == 0:
        print("    (无缓存需要清除)")
    else:
        print(f"    共清除 {total_cleared} 条缓存")
    return total_cleared


def _get_internal_secret() -> str | None:
    """读取后端的 QUICK_CHART_INTERNAL_SECRET 配置"""
    try:
        from app.core.config import settings
        return getattr(settings, "QUICK_CHART_INTERNAL_SECRET", None)
    except Exception:
        return None


def _http_get(url: str, timeout: float = 120.0, headers: dict | None = None) -> int:
    """发起 GET 请求，返回 HTTP 状态码。使用 urllib（stdlib）无需额外依赖。"""
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    req = Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        resp = urlopen(req, timeout=timeout)
        _ = resp.read()
        return resp.status
    except HTTPError as e:
        return e.code
    except URLError:
        raise


def warm_up_cache():
    """通过内部 API 在后台直接刷新缓存（清空后按配置重新计算并写入），无需通过 Web。"""
    secret = _get_internal_secret()
    print(f"\n  刷新缓存 (后端: {BASE_URL}, 内部 API)...")
    if not secret:
        print("    ⚠ 未配置 QUICK_CHART_INTERNAL_SECRET，无法调用内部 API，跳过预热")
        return 0

    try:
        _http_get(f"{BASE_URL}/health", timeout=5.0)
    except Exception:
        print("    ⚠ 后端不可达，跳过缓存刷新")
        print(f"    请确保后端已启动: cd backend && uvicorn main:app --port 8000")
        return 0

    url = f"{BASE_URL}/api/internal/refresh-chart-cache"
    req = __import__("urllib.request", fromlist=["Request"]).Request(
        url, data=None, method="POST", headers={"X-Quick-Chart-Secret": secret}
    )
    try:
        t1 = time.time()
        resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(req, timeout=900.0)
        body = resp.read().decode("utf-8")
        elapsed = time.time() - t1
        if 200 <= resp.status < 300:
            import json
            data = json.loads(body)
            print(f"    清除 {data.get('cleared', 0)} 条，重新计算 {data.get('computed', 0)} 条 ({elapsed:.1f}s)")
            return data.get("computed", 0)
        print(f"    ✗ HTTP {resp.status} ({elapsed:.1f}s)")
        return 0
    except Exception as e:
        print(f"    调用刷新接口失败: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="HogPrice 数据导入 + 缓存刷新",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python import_data.py                                    # 增量导入默认目录
  python import_data.py /path/to/data                      # 增量导入指定目录
  python import_data.py --mode bulk                        # 全量导入（清空+重导）
  python import_data.py --files "涌益咨询日度数据.xlsx"      # 只导入指定文件
  python import_data.py --skip-warmup                      # 导入后不预热缓存
        """,
    )
    parser.add_argument(
        "source_dir",
        nargs="?",
        default=DEFAULT_SOURCE_DIR,
        help=f"数据源目录 (默认: {DEFAULT_SOURCE_DIR})",
    )
    parser.add_argument(
        "--mode",
        choices=["incremental", "bulk"],
        default="incremental",
        help="导入模式: incremental=增量(默认) | bulk=全量(TRUNCATE+INSERT)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="指定要导入的文件名（默认全部）",
    )
    parser.add_argument(
        "--skip-warmup",
        action="store_true",
        help="跳过缓存预热（仅清除缓存，不请求后端）",
    )

    args = parser.parse_args()

    # 校验目录
    if not os.path.isdir(args.source_dir):
        print(f"✗ 数据目录不存在: {args.source_dir}")
        sys.exit(1)

    mode_label = "增量导入" if args.mode == "incremental" else "全量导入"
    print_header(
        f"数据导入 + 缓存刷新",
        f"模式: {mode_label} | 数据目录: {args.source_dir}",
    )

    engine = get_engine()
    t_total = time.time()

    # ── Step 1: 导入数据 ──
    if args.mode == "bulk":
        run_bulk(engine, args.source_dir, args.files)
    else:
        run_incremental_import(engine, args.source_dir, args.files)

    # ── Step 2: 清除缓存 ──
    clear_cache(engine)

    # ── Step 3: 预热缓存 ──
    warmed = 0
    if not args.skip_warmup:
        warmed = warm_up_cache()
    else:
        print("\n  (已跳过缓存预热)")

    # ── 总结 ──
    total_elapsed = time.time() - t_total
    print_header(
        f"全部完成！耗时 {total_elapsed:.1f}s",
        f"预热 {warmed} 个接口" if warmed else "",
    )


if __name__ == "__main__":
    main()
