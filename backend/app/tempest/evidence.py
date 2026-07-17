"""Decision evidence intake — inject qualitative/quantitative info into decisioning."""

from __future__ import annotations

import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.tempest.decision import DecisionCase, QualSignal, QuantSignal


class EvidenceIntakeStore:
    """In-process store of user-submitted evidence that feeds decision structures."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    def upsert(self, item: dict[str, Any]) -> dict[str, Any]:
        """Insert or replace by evidence_id (used when hydrating from DB)."""
        normalized = self._normalize({**item, "evidence_id": item.get("evidence_id")})
        self._items[normalized["evidence_id"]] = normalized
        return normalized

    def list(
        self,
        *,
        case_id: str | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        rows = list(self._items.values())
        if case_id:
            rows = [r for r in rows if r.get("case_id") in (case_id, None, "", "*")]
        if kind:
            rows = [r for r in rows if r.get("kind") == kind]
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return rows[: max(1, min(limit, 200))]

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        return self._items.get(evidence_id)

    def add(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = self._normalize(payload)
        self._items[item["evidence_id"]] = item
        return item

    def add_many(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.add(p) for p in payloads]

    def delete(self, evidence_id: str) -> bool:
        return self._items.pop(evidence_id, None) is not None

    def clear(self, case_id: str | None = None) -> int:
        if case_id is None:
            n = len(self._items)
            self._items.clear()
            return n
        drop = [k for k, v in self._items.items() if v.get("case_id") == case_id]
        for k in drop:
            del self._items[k]
        return len(drop)

    def ingest_free_text(
        self,
        *,
        text: str,
        case_id: str | None = None,
        source: str = "user_input",
        submitted_by: str = "demo-user-001",
        decision_relevance: str = "",
    ) -> dict[str, Any]:
        """Heuristic classify free text into quant or qual evidence for decisions."""
        t = text.strip()
        quant = self._try_parse_quant(t)
        if quant:
            return self.add(
                {
                    "kind": "quantitative",
                    "case_id": case_id,
                    "title": quant["name"],
                    "source": source,
                    "submitted_by": submitted_by,
                    "decision_relevance": decision_relevance or "ユーザー投入の定量指標",
                    **quant,
                }
            )
        polarity = "mixed"
        if any(k in t for k in ("強み", "改善", "好調", "安定", "前向き", "増産", "提携")):
            polarity = "positive"
        if any(k in t for k in ("懸念", "悪化", "警戒", "依存", "圧迫", "赤字", "延滞")):
            polarity = "negative"
        title = t[:40] + ("…" if len(t) > 40 else "")
        kind = "news" if any(k in t for k in ("報道", "ニュース", "発表", "開示")) else "qualitative"
        return self.add(
            {
                "kind": kind,
                "case_id": case_id,
                "title": title or "定性エビデンス",
                "narrative": t,
                "polarity": polarity,
                "confidence": 0.75,
                "source": source,
                "submitted_by": submitted_by,
                "decision_relevance": decision_relevance or "ユーザー投入の定性情報",
                "weight": 1.1,
            }
        )

    def apply_to_case(self, case: DecisionCase) -> tuple[DecisionCase, list[dict[str, Any]]]:
        """Return a deep-copied case with ingested evidence merged into signal lists."""
        merged = deepcopy(case)
        unique: list[dict[str, Any]] = []
        for row in self._items.values():
            cid = row.get("case_id")
            if cid not in (None, "", "*", case.case_id):
                continue
            unique.append(row)
        unique.sort(key=lambda r: r.get("created_at") or "")

        for row in unique:
            sid = row["evidence_id"][:12]
            if row["kind"] == "quantitative":
                merged.quant_signals.append(
                    QuantSignal(
                        signal_id=sid,
                        name=row.get("title") or row.get("name") or "投入定量",
                        value=float(row.get("value") or 0),
                        unit=str(row.get("unit") or "index"),
                        source=str(row.get("source") or "user"),
                        trend=str(row.get("trend") or "flat"),
                        weight=float(row.get("weight") or 1.0),
                    )
                )
            else:
                merged.qual_signals.append(
                    QualSignal(
                        signal_id=sid,
                        name=row.get("title") or "投入定性",
                        narrative=str(row.get("narrative") or row.get("content") or ""),
                        polarity=str(row.get("polarity") or "mixed"),
                        source=str(row.get("source") or "user"),
                        confidence=float(row.get("confidence") or 0.7),
                        weight=float(row.get("weight") or 1.0),
                    )
                )
        return merged, unique

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        kind = str(payload.get("kind") or "qualitative").lower()
        if kind not in ("quantitative", "qualitative", "news", "note"):
            kind = "qualitative"
        eid = str(payload.get("evidence_id") or f"EV-{uuid.uuid4().hex[:10].upper()}")
        item: dict[str, Any] = {
            "evidence_id": eid,
            "kind": kind,
            "case_id": payload.get("case_id") or None,
            "title": str(payload.get("title") or payload.get("name") or "意思決定エビデンス"),
            "source": str(payload.get("source") or "user_input"),
            "submitted_by": str(payload.get("submitted_by") or "demo-user-001"),
            "decision_relevance": str(payload.get("decision_relevance") or ""),
            "weight": float(payload.get("weight") or 1.0),
            "created_at": payload.get("created_at")
            or datetime.now(timezone.utc).isoformat(),
        }
        if kind == "quantitative":
            if payload.get("value") is None:
                raise ValueError("quantitative evidence requires value")
            value = float(payload["value"])
            unit = str(payload.get("unit") or "index")
            if unit in ("%", "％"):
                value = value / 100.0
                unit = "ratio"
            item.update(
                {
                    "value": value,
                    "unit": unit,
                    "trend": str(payload.get("trend") or "flat"),
                    "name": item["title"],
                }
            )
        else:
            narrative = str(payload.get("narrative") or payload.get("content") or "")
            if not narrative:
                raise ValueError("qualitative/news/note evidence requires narrative or content")
            item.update(
                {
                    "narrative": narrative,
                    "polarity": str(payload.get("polarity") or "mixed"),
                    "confidence": float(payload.get("confidence") or 0.75),
                }
            )
        return item

    @staticmethod
    def _try_parse_quant(text: str) -> dict[str, Any] | None:
        # e.g. "DSCR=1.1" / "自己資本比率 18%" / "業況DI: -3"
        m = re.search(
            r"([^\s:=：]{2,24})\s*[=:：]\s*(-?\d+(?:\.\d+)?)\s*(%|％|倍|x|X)?",
            text,
        )
        if not m:
            m = re.search(r"(-?\d+(?:\.\d+)?)\s*(%|％)\s*の?\s*([^\s。]{2,16})", text)
            if m:
                return {
                    "name": m.group(3),
                    "value": float(m.group(1)) / 100.0,
                    "unit": "ratio",
                    "trend": "flat",
                }
            return None
        name, val_s, unit_raw = m.group(1), m.group(2), m.group(3)
        value = float(val_s)
        unit = "index"
        if unit_raw in ("%", "％"):
            value = value / 100.0
            unit = "ratio"
        elif unit_raw and unit_raw.lower() in ("x", "倍"):
            unit = "x"
        elif "比率" in name or "率" in name:
            if value > 1.5:
                value = value / 100.0
            unit = "ratio"
        elif name.upper() == "DSCR" or "DSCR" in name.upper():
            unit = "x"
        return {"name": name, "value": value, "unit": unit, "trend": "flat"}


evidence_store = EvidenceIntakeStore()
