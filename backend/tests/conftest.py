"""Shared fixtures for unit tests (no live DB required)."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend/ is on sys.path when pytest is invoked from repo root or backend/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
