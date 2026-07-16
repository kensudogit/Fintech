"""Web-accessible test execution and Python source inventory."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.testing.inventory import list_python_sources
from app.testing.runner import HTML_REPORT, JSON_REPORT, get_latest_report, is_running, run_tests

router = APIRouter(tags=["tests"])
_executor = ThreadPoolExecutor(max_workers=1)


@router.get("/tests/status")
async def tests_status() -> dict:
    return get_latest_report()


@router.get("/tests/report")
async def tests_report_json() -> dict:
    if not JSON_REPORT.exists():
        raise HTTPException(status_code=404, detail="no report yet — POST /api/v1/tests/run first")
    try:
        return json.loads(JSON_REPORT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="invalid report json") from exc


@router.get("/tests/sources")
async def tests_sources() -> list[dict]:
    return list_python_sources()


@router.post("/tests/run")
async def tests_run(
    background: BackgroundTasks,
    wait: bool = Query(default=True, description="true なら完了まで待機して結果を返す"),
) -> dict:
    if is_running():
        return {"ok": False, "error": "tests already running", "running": True}

    if wait:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(_executor, run_tests)
        return result

    background.add_task(lambda: run_tests())
    return {"ok": True, "accepted": True, "running": True, "hint": "GET /api/v1/tests/status"}
