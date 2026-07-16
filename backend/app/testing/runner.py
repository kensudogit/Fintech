"""Run pytest and persist HTML/JSON reports for the web UI."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = BACKEND_ROOT / "reports"
HTML_REPORT = REPORTS_DIR / "pytest-report.html"
JSON_REPORT = REPORTS_DIR / "pytest-report.json"
JUNIT_REPORT = REPORTS_DIR / "pytest-junit.xml"
LATEST_META = REPORTS_DIR / "latest.json"

_lock = threading.Lock()
_running = False
_last_proc: dict[str, Any] | None = None


def reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def is_running() -> bool:
    return _running


def get_latest_report() -> dict[str, Any]:
    reports_dir()
    meta: dict[str, Any] = {}
    if LATEST_META.exists():
        try:
            meta = json.loads(LATEST_META.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta.update(
        {
            "running": _running,
            "html_exists": HTML_REPORT.exists(),
            "json_exists": JSON_REPORT.exists(),
            "html_url": "/tests/report",
            "json_url": "/api/v1/tests/report",
            "junit_exists": JUNIT_REPORT.exists(),
        }
    )
    if JSON_REPORT.exists():
        try:
            meta["summary"] = json.loads(JSON_REPORT.read_text(encoding="utf-8")).get("summary")
        except json.JSONDecodeError:
            pass
    return meta


def run_tests(*, args: list[str] | None = None, timeout_sec: int = 180) -> dict[str, Any]:
    """Execute pytest; write HTML + JSON summary. Thread-safe single flight."""
    global _running, _last_proc
    with _lock:
        if _running:
            return {"ok": False, "error": "tests already running", "running": True}
        _running = True

    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    reports_dir()

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-q",
        "--tb=short",
        f"--html={HTML_REPORT}",
        "--self-contained-html",
        f"--junitxml={JUNIT_REPORT}",
    ]
    if args:
        cmd.extend(args)

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            check=False,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        summary = _parse_junit(JUNIT_REPORT)
        if summary["total"] == 0:
            summary = _parse_pytest_output(proc.stdout, proc.stderr, proc.returncode)
        else:
            summary["exit_code"] = proc.returncode
            summary["raw_tail"] = (proc.stdout or "").strip().splitlines()[-5:]
        payload = {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": elapsed_ms,
            "command": cmd,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-4000:],
            "summary": summary,
            "html_report": str(HTML_REPORT.relative_to(BACKEND_ROOT)).replace("\\", "/"),
            "junit_report": str(JUNIT_REPORT.relative_to(BACKEND_ROOT)).replace("\\", "/"),
        }
        JSON_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        LATEST_META.write_text(
            json.dumps(
                {
                    "ok": payload["ok"],
                    "exit_code": payload["exit_code"],
                    "started_at": payload["started_at"],
                    "finished_at": payload["finished_at"],
                    "elapsed_ms": payload["elapsed_ms"],
                    "summary": summary,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        _last_proc = payload
        return payload
    except subprocess.TimeoutExpired as exc:
        payload = {
            "ok": False,
            "error": f"timeout after {timeout_sec}s",
            "started_at": started_at,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        }
        JSON_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
    finally:
        with _lock:
            _running = False


def _parse_junit(path: Path) -> dict[str, Any]:
    import xml.etree.ElementTree as ET

    summary = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "total": 0, "exit_code": 0, "raw_tail": []}
    if not path.exists():
        return summary
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return summary
    # root may be testsuite or testsuites
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    for suite in suites:
        tests = int(suite.attrib.get("tests", 0))
        failures = int(suite.attrib.get("failures", 0))
        errors = int(suite.attrib.get("errors", 0))
        skipped = int(suite.attrib.get("skipped", 0))
        summary["total"] += tests
        summary["failed"] += failures
        summary["errors"] += errors
        summary["skipped"] += skipped
        summary["passed"] += max(0, tests - failures - errors - skipped)
    return summary


def _parse_pytest_output(stdout: str, stderr: str, exit_code: int) -> dict[str, Any]:
    """Best-effort parse of pytest -q summary line."""
    import re

    text = (stdout or "") + "\n" + (stderr or "")
    summary = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": exit_code,
        "raw_tail": text.strip().splitlines()[-5:] if text.strip() else [],
    }
    for line in reversed(text.splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            for kind, key in (
                ("passed", "passed"),
                ("failed", "failed"),
                ("skipped", "skipped"),
                ("error", "errors"),
            ):
                mm = re.search(rf"(\d+)\s+{kind}", line)
                if mm:
                    summary[key] = int(mm.group(1))
            break
    # Fallback: count progress dots when only quiet output is available
    if summary["passed"] == 0 and summary["failed"] == 0 and exit_code == 0:
        dots = sum(line.count(".") for line in text.splitlines() if set(line.strip()) <= {".", " "})
        if dots:
            summary["passed"] = dots
    summary["total"] = summary["passed"] + summary["failed"] + summary["errors"] + summary["skipped"]
    return summary
