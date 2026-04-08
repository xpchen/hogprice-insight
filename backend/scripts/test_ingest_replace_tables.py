#!/usr/bin/env python3
"""
自测 Web 导入「覆盖导入」replace_tables 行为。

前置：本机已启动 API（默认 http://127.0.0.1:8000），MySQL 可连，存在 admin 账号（与 test_api_auth 一致）。
导入接口路径为 /api/ingest/*（与 settings.API_V1_STR=/api 一致，非 /api/v1）。

用法（在 backend 目录）:
  python scripts/test_ingest_replace_tables.py
环境变量:
  API_BASE=http://127.0.0.1:8000
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import openpyxl
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
INGEST_EXECUTE = f"{DEFAULT_BASE}/api/ingest/execute"
INGEST_SUBMIT = f"{DEFAULT_BASE}/api/ingest/submit"
LOGIN_URL = f"{DEFAULT_BASE}/api/auth/login"


def _minimal_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def _login() -> str:
    r = requests.post(
        LOGIN_URL,
        data={"username": "admin", "password": "Admin@123"},
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(f"登录失败 {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]


def main() -> int:
    print("API:", DEFAULT_BASE)
    try:
        token = _login()
    except Exception as e:
        print("SKIP/FAIL: 无法登录（请先启动后端并确认 admin 密码）:", e)
        return 1

    headers = {"Authorization": f"Bearer {token}"}
    dummy = _minimal_xlsx_bytes()

    # 1) 覆盖 + 不支持模板 → 400
    r1 = requests.post(
        INGEST_EXECUTE,
        headers=headers,
        params={"template_type": "GANGLIAN_DAILY", "replace_tables": True},
        files={"file": ("dummy_ganglian.xlsx", dummy, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=120,
    )
    print("1) GANGLIAN_DAILY + replace_tables=true ->", r1.status_code)
    if r1.status_code != 400:
        print("   期望 400，实际:", r1.text[:500])
        return 1
    detail = r1.json().get("detail", "")
    if "不支持" not in detail and "覆盖" not in detail:
        print("   响应 detail 异常:", detail[:300])
        return 1
    print("   OK:", detail[:120])

    # 2) 同请求但不覆盖 → 应进入导入（可能因空 xlsx 失败 500，不得 400）
    r2 = requests.post(
        INGEST_EXECUTE,
        headers=headers,
        params={"template_type": "GANGLIAN_DAILY", "replace_tables": False},
        files={"file": ("dummy_ganglian.xlsx", dummy, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=120,
    )
    print("2) GANGLIAN_DAILY + replace_tables=false ->", r2.status_code, "(empty xlsx, expect not 400)")
    if r2.status_code == 400:
        print("   不应因 replace 被拒:", r2.text[:300])
        return 1

    # 3) 3.2 真实文件 + 覆盖 → 应成功（会 TRUNCATE fact_enterprise_monthly）
    xlsx = REPO_ROOT / "docs" / "3.2、集团企业月度数据跟踪.xlsx"
    if not xlsx.is_file():
        print("3) SKIP: 未找到", xlsx)
        print("--- 前两项已通过 ---")
        return 0

    with open(xlsx, "rb") as f:
        body = f.read()
    r3 = requests.post(
        INGEST_EXECUTE,
        headers=headers,
        params={"template_type": "ENTERPRISE_MONTHLY", "replace_tables": True},
        files={
            "file": (
                xlsx.name,
                body,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        timeout=600,
    )
    print("3) ENTERPRISE_MONTHLY + replace + real 3.2 ->", r3.status_code)
    if r3.status_code != 200:
        print("   ", r3.text[:500])
        return 1
    j = r3.json()
    print("   inserted 行(合计):", j.get("inserted"), "|", (j.get("message") or "")[:80])

    # 4) submit 多文件表单带 replace_tables=1（单文件 3.2）
    files_m = [("files", (xlsx.name, body, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]
    data_m = [("replace_tables", "1")]
    r4 = requests.post(
        INGEST_SUBMIT,
        headers=headers,
        files=files_m,
        data=data_m,
        timeout=60,
    )
    print("4) POST /ingest/submit replace_tables=1 ->", r4.status_code)
    if r4.status_code not in (200, 202):
        print("   ", r4.text[:400])
        return 1
    task_id = r4.json().get("task_id")
    print("   task_id:", task_id)

    print("--- self-test OK ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
