"""
执行一次 3.2、集团企业月度数据跟踪.xlsx 导入到 fact_enterprise_monthly。
用法（在项目根目录）: python -m backend.scripts.run_enterprise_monthly_import
或（在 backend 目录）: python -m scripts.run_enterprise_monthly_import
"""
import sys
import time
from pathlib import Path

# 项目/backend 路径
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
repo_root = backend_dir.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(backend_dir))

def main():
    from sqlalchemy import text
    from app.core.database import engine
    from import_tool.readers.r04_enterprise_monthly import EnterpriseMonthlyReader

    excel_name = "3.2、集团企业月度数据跟踪.xlsx"
    # 优先 docs/0306_生猪/生猪/
    search_dirs = [
        repo_root / "docs" / "0306_生猪" / "生猪",
        repo_root / "docs" / "生猪" / "集团企业",
        repo_root / "docs" / "生猪",
    ]
    filepath = None
    for d in search_dirs:
        if d.exists():
            p = d / excel_name
            if p.exists():
                filepath = str(p)
                break
    if not filepath:
        print(f"未找到文件: {excel_name}")
        print("已查找目录:", [str(d) for d in search_dirs])
        return 1

    print("=" * 60)
    print("执行集团企业月度导入 (3.2)")
    print("=" * 60)
    print(f"文件: {filepath}")

    # 先删「汇总」对应数据，再插入，保证展示与 Excel 汇总 sheet 一模一样
    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM fact_enterprise_monthly
            WHERE company_code = 'TOTAL' AND region_code IN ('GUANGDONG','SICHUAN','GUIZHOU')
        """))
        conn.commit()
    print("  已清除库内汇总数据，将以 Excel 为准重新写入")

    batch_id = 1
    with engine.connect() as conn:
        r = conn.execute(text(
            "INSERT INTO import_batch (filename, mode, status) VALUES (:f, 'incremental', 'processing')"
        ), {"f": excel_name})
        conn.commit()
        batch_id = r.lastrowid

    t0 = time.time()
    try:
        reader = EnterpriseMonthlyReader(engine, batch_id)
        results = reader.read_file(filepath)
        counts = reader.insert_all(results, mode="bulk")
        total = sum(counts.values())
        elapsed = time.time() - t0
        for table, n in counts.items():
            if n > 0:
                print(f"  {table}: {n} 行")
        print(f"✓ 导入完成，共 {total} 行，耗时 {elapsed:.1f}s")

        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE import_batch SET status='success', row_count=:r, duration_ms=:d WHERE id=:id"
            ), {"r": total, "d": int(elapsed * 1000), "id": batch_id})
            conn.commit()
    except Exception as e:
        elapsed = time.time() - t0
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE import_batch SET status='failed', duration_ms=:d, error_msg=:e WHERE id=:id"
            ), {"d": int(elapsed * 1000), "e": str(e)[:500], "id": batch_id})
            conn.commit()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
