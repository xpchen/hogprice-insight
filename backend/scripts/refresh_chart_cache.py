#!/usr/bin/env python3
"""
在后台直接刷新图表缓存（quick_chart_cache），无需通过 Web 操作。

用法（需先启动后端）:
  cd backend && python scripts/refresh_chart_cache.py
  或
  cd backend && python -m scripts.refresh_chart_cache

会清空 quick_chart_cache 并按 QUICK_CHART_PRECOMPUTE_URLS 重新请求接口并写入缓存。
需在 .env 中配置 QUICK_CHART_INTERNAL_SECRET，且后端服务已启动（默认 http://127.0.0.1:8000）。
"""
import os
import sys

# 确保 backend 为可导入根
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    try:
        from dotenv import load_dotenv
        # 从 backend 目录加载 .env
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_dotenv(os.path.join(backend_dir, ".env"))
        from app.core.config import settings
        secret = getattr(settings, "QUICK_CHART_INTERNAL_SECRET", None) or os.environ.get("QUICK_CHART_INTERNAL_SECRET")
        if not secret:
            print("未配置 QUICK_CHART_INTERNAL_SECRET，请在 .env 中设置")
            sys.exit(1)
    except Exception as e:
        print("加载配置失败:", e)
        sys.exit(1)

    base_url = os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    url = f"{base_url}/api/internal/refresh-chart-cache"

    try:
        import httpx
        with httpx.Client(timeout=900.0) as client:
            r = client.post(url, headers={"X-Quick-Chart-Secret": secret})
            r.raise_for_status()
            data = r.json()
    except httpx.ConnectError:
        print("无法连接后端，请先启动服务: cd backend && uvicorn main:app --port 8000")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"请求失败 HTTP {e.response.status_code}: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print("请求失败:", e)
        sys.exit(1)

    print("图表缓存已刷新")
    print(f"  清除: {data.get('cleared', 0)} 条")
    print(f"  重新计算: {data.get('computed', 0)} 条")
    errors = data.get("errors") or []
    if errors:
        print(f"  失败: {len(errors)} 个")
        for err in errors[:5]:
            print(f"    - {err.get('path', '')} {err.get('error', '')}")
        if len(errors) > 5:
            print(f"    ... 共 {len(errors)} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
