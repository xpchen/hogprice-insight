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
import time
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


def _wait_task_done(task_id: str, token: str, timeout_sec: int = 40) -> dict:
    """通过 SSE 等待任务结束，返回最后一条 data json。"""
    url = f"{DEFAULT_BASE}/api/ingest/sse/{task_id}?token={token}"
    deadline = time.time() + timeout_sec
    with requests.get(url, stream=True, timeout=timeout_sec) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"SSE 连接失败 {resp.status_code}: {resp.text[:200]}")
        last: dict = {}
        for raw in resp.iter_lines(decode_unicode=True):
            if time.time() > deadline:
                raise TimeoutError(f"等待任务超时: {task_id}")
            if not raw:
                continue
            if not raw.startswith("data: "):
                continue
            payload = raw[6:]
            try:
                import json

                data = json.loads(payload)
            except Exception:
                continue
            last = data
            if data.get("status") == "done":
                return data
    return last


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

    # 2) 新增支持模板：YONGYI_DAILY + 覆盖（空 xlsx 下也不应 400 拒绝）
    r2 = requests.post(
        INGEST_EXECUTE,
        headers=headers,
        params={"template_type": "YONGYI_DAILY", "replace_tables": True},
        files={"file": ("涌益咨询日度数据.xlsx", dummy, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=120,
    )
    print("2) YONGYI_DAILY + replace_tables=true ->", r2.status_code, "(empty xlsx, expect not 400)")
    if r2.status_code == 400:
        print("   新增支持模板不应被拒:", r2.text[:300])
        return 1

    # 3) 同请求但不覆盖 → 应进入导入（可能因空 xlsx 失败 500，不得 400）
    r2 = requests.post(
        INGEST_EXECUTE,
        headers=headers,
        params={"template_type": "GANGLIAN_DAILY", "replace_tables": False},
        files={"file": ("dummy_ganglian.xlsx", dummy, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=120,
    )
    print("3) GANGLIAN_DAILY + replace_tables=false ->", r2.status_code, "(empty xlsx, expect not 400)")
    if r2.status_code == 400:
        print("   不应因 replace 被拒:", r2.text[:300])
        return 1

    # 4) 3.2 真实文件 + 覆盖 → 应成功（会 TRUNCATE fact_enterprise_monthly）
    xlsx = REPO_ROOT / "docs" / "3.2、集团企业月度数据跟踪.xlsx"
    if not xlsx.is_file():
        print("4) SKIP: 未找到", xlsx)
        print("--- 前两项已通过 ---")
    else:
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
        print("4) ENTERPRISE_MONTHLY + replace + real 3.2 ->", r3.status_code)
        if r3.status_code != 200:
            print("   ", r3.text[:500])
            return 1
        j = r3.json()
        print("   inserted 行(合计):", j.get("inserted"), "|", (j.get("message") or "")[:100])

    # 5) submit 混合文件 + replace=1（应失败且给出具体文件）
    files_mixed = [
        ("files", ("涌益咨询日度数据.xlsx", dummy, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("files", ("1、价格：钢联自动更新模板.xlsx", dummy, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
    ]
    r4 = requests.post(
        INGEST_SUBMIT,
        headers=headers,
        files=files_mixed,
        data=[("replace_tables", "1")],
        timeout=60,
    )
    print("5) POST /ingest/submit mixed files + replace_tables=1 ->", r4.status_code)
    if r4.status_code not in (200, 202):
        print("   ", r4.text[:400])
        return 1
    task_id = r4.json().get("task_id")
    print("   task_id:", task_id)
    done_data = _wait_task_done(task_id, token)
    print("   done:", done_data)
    if done_data.get("success") is not False:
        print("   期望 mixed 场景失败，实际:", done_data)
        return 1
    msg = str(done_data.get("message", ""))
    if "钢联" not in msg and "GANGLIAN_DAILY" not in msg:
        print("   失败消息缺少具体文件/模板:", msg)
        return 1

    # 6) execute 单文件支持模板 + replace=1（应受理）
    r5 = requests.post(
        INGEST_EXECUTE,
        headers=headers,
        params={"template_type": "YONGYI_DAILY", "replace_tables": True},
        files={"file": ("涌益咨询日度数据.xlsx", dummy, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=120,
    )
    print("6) YONGYI_DAILY execute + replace_tables=true ->", r5.status_code)
    if r5.status_code == 400:
        print("   不应被 400 拒绝:", r5.text[:300])
        return 1

    print("--- self-test OK ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
