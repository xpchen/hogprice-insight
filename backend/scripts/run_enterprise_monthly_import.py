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
    # 优先项目 docs 根目录（用户常粘贴到此），再查生猪子目录
    search_dirs = [
        repo_root / "docs",
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

    # 仅本表全量：truncate 后整文件 bulk 写入（避免 INSERT IGNORE 留旧值）
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE fact_enterprise_monthly"))
        conn.commit()
    print("  已清空 fact_enterprise_monthly，将以当前 Excel 全量写入")

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
