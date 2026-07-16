"""Inventory of all Python sources under backend/ for web browsing."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", "reports", "data", "node_modules"}


def list_python_sources(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or BACKEND_ROOT
    rows: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(base).as_posix()
        info = _inspect(path)
        rows.append(
            {
                "path": rel,
                "module": rel.replace("/", ".").removesuffix(".py"),
                "lines": info["lines"],
                "docstring": info["docstring"],
                "classes": info["classes"],
                "functions": info["functions"],
                "has_tests": _has_tests(rel),
            }
        )
    return rows


def _has_tests(rel_path: str) -> bool:
    name = Path(rel_path).stem
    if name.startswith("test_"):
        return True
    # Heuristic: tempest/loan.py -> test_tempest_loan.py etc.
    candidates = [
        f"tests/test_{name}.py",
        f"tests/test_{rel_path.replace('/', '_').replace('.py', '')}.py",
    ]
    # Broader: any test file mentioning the module stem
    test_dir = BACKEND_ROOT / "tests"
    if not test_dir.exists():
        return False
    for p in test_dir.glob("test_*.py"):
        if name in p.stem or name.replace("_", "") in p.stem.replace("_", ""):
            return True
    return any((BACKEND_ROOT / c).exists() for c in candidates)


def _inspect(path: Path) -> dict[str, Any]:
    try:
        src = path.read_text(encoding="utf-8")
    except OSError:
        return {"lines": 0, "docstring": "", "classes": [], "functions": []}
    lines = src.count("\n") + (1 if src and not src.endswith("\n") else 0)
    docstring = ""
    classes: list[str] = []
    functions: list[str] = []
    try:
        tree = ast.parse(src)
        docstring = ast.get_docstring(tree) or ""
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    functions.append(node.name)
    except SyntaxError:
        pass
    return {
        "lines": lines,
        "docstring": docstring.strip().splitlines()[0] if docstring.strip() else "",
        "classes": classes[:20],
        "functions": functions[:30],
    }
