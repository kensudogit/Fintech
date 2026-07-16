"""Demo financial operation tools with confirmation workflow (no real money movement)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DemoAccount:
    account_id: str
    name: str
    balance: int
    currency: str = "JPY"


@dataclass
class PendingAction:
    action_id: str
    external_id: str
    action_type: str
    params: dict[str, Any]
    summary: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FinanceToolkit:
    """In-memory demo ledger + pending confirmations (per process)."""

    def __init__(self) -> None:
        self._accounts: dict[str, list[DemoAccount]] = {}
        self._pending: dict[str, PendingAction] = {}

    def ensure_accounts(self, external_id: str) -> list[DemoAccount]:
        if external_id not in self._accounts:
            self._accounts[external_id] = [
                DemoAccount("ACC-普通-001", "普通預金", 428_500),
                DemoAccount("ACC-積立-001", "つみたて用口座", 120_000),
            ]
        return self._accounts[external_id]

    def get_balances(self, external_id: str) -> dict[str, Any]:
        accounts = self.ensure_accounts(external_id)
        return {
            "external_id": external_id,
            "accounts": [
                {
                    "account_id": a.account_id,
                    "name": a.name,
                    "balance": a.balance,
                    "currency": a.currency,
                }
                for a in accounts
            ],
            "total_balance": sum(a.balance for a in accounts),
        }

    def parse_operation(self, query: str, external_id: str) -> dict[str, Any]:
        """Interpret NL into a structured operation plan (draft only)."""
        q = query
        accounts = self.ensure_accounts(external_id)

        if any(k in q for k in ("残高", "いくら", "balance")):
            balances = self.get_balances(external_id)
            return {
                "action_type": "check_balance",
                "needs_confirmation": False,
                "result": balances,
                "message": (
                    "残高照会結果です。\n"
                    + "\n".join(
                        f"・{a['name']}（{a['account_id']}）: ¥{a['balance']:,}"
                        for a in balances["accounts"]
                    )
                    + f"\n合計: ¥{balances['total_balance']:,}"
                ),
            }

        if any(k in q for k in ("カード停止", "カードを止め", "不正", "freeze", "利用停止")):
            action = self._create_pending(
                external_id,
                "freeze_card",
                {"card_id": "CARD-001", "reason": "user_request"},
                "クレジットカード CARD-001 を一時停止します。確認後に実行されます。",
            )
            return {
                "action_type": "freeze_card",
                "needs_confirmation": True,
                "pending_action": self._pending_dict(action),
                "message": (
                    "カード一時停止の下書きを作成しました。\n"
                    f"確認ID: {action.action_id}\n"
                    "実行するには「確認する」または API で confirm してください。"
                ),
            }

        amount = self._extract_amount(q)
        if any(k in q for k in ("振込", "送金", "振り込", "transfer", "pay")) and amount:
            dest = "指定口座"
            m = re.search(r"(.+?)[へに].{0,24}?(?:を)?(?:振込|送金|振り込)", q)
            if m:
                dest = re.sub(r"^(?:から|より)", "", m.group(1).strip())[-20:] or dest
            source = accounts[0]
            action = self._create_pending(
                external_id,
                "transfer",
                {
                    "from_account": source.account_id,
                    "to": dest,
                    "amount": amount,
                    "currency": "JPY",
                },
                f"{source.name} から {dest} へ ¥{amount:,} を振り込みます。",
            )
            return {
                "action_type": "transfer",
                "needs_confirmation": True,
                "pending_action": self._pending_dict(action),
                "message": (
                    "振込の下書きを作成しました（未実行）。\n"
                    f"・出金口座: {source.name}（残高 ¥{source.balance:,}）\n"
                    f"・振込先: {dest}\n"
                    f"・金額: ¥{amount:,}\n"
                    f"確認ID: {action.action_id}\n"
                    "内容を確認のうえ「確認する」と入力してください。"
                ),
            }

        return {
            "action_type": "guide",
            "needs_confirmation": False,
            "message": (
                "実行可能な操作: 残高確認 / 振込（金額指定） / カード一時停止。\n"
                "例:「残高を教えて」「太郎へ3000円振り込みたい」「カードを一時停止して」"
            ),
        }

    def confirm(self, action_id: str) -> dict[str, Any]:
        action = self._pending.get(action_id)
        if not action:
            return {"ok": False, "error": "pending action not found"}
        if action.status != "pending":
            return {"ok": False, "error": f"action already {action.status}", "action": self._pending_dict(action)}

        if action.action_type == "transfer":
            accounts = self.ensure_accounts(action.external_id)
            amount = int(action.params.get("amount", 0))
            from_id = action.params.get("from_account")
            src = next((a for a in accounts if a.account_id == from_id), accounts[0])
            if src.balance < amount:
                action.status = "failed"
                return {"ok": False, "error": "insufficient funds", "action": self._pending_dict(action)}
            src.balance -= amount
            action.status = "executed"
            return {
                "ok": True,
                "message": f"振込を実行しました（デモ）。{src.name} 残高: ¥{src.balance:,}",
                "action": self._pending_dict(action),
                "balances": self.get_balances(action.external_id),
            }

        if action.action_type == "freeze_card":
            action.status = "executed"
            return {
                "ok": True,
                "message": f"カード {action.params.get('card_id')} を一時停止しました（デモ）。",
                "action": self._pending_dict(action),
            }

        action.status = "executed"
        return {"ok": True, "message": "操作を実行しました（デモ）。", "action": self._pending_dict(action)}

    def cancel(self, action_id: str) -> dict[str, Any]:
        action = self._pending.get(action_id)
        if not action:
            return {"ok": False, "error": "pending action not found"}
        action.status = "cancelled"
        return {"ok": True, "action": self._pending_dict(action)}

    def list_pending(self, external_id: str) -> list[dict[str, Any]]:
        return [
            self._pending_dict(a)
            for a in self._pending.values()
            if a.external_id == external_id and a.status == "pending"
        ]

    def _create_pending(
        self,
        external_id: str,
        action_type: str,
        params: dict[str, Any],
        summary: str,
    ) -> PendingAction:
        action = PendingAction(
            action_id=f"PA-{uuid.uuid4().hex[:8].upper()}",
            external_id=external_id,
            action_type=action_type,
            params=params,
            summary=summary,
        )
        self._pending[action.action_id] = action
        return action

    @staticmethod
    def _pending_dict(action: PendingAction) -> dict[str, Any]:
        return {
            "action_id": action.action_id,
            "external_id": action.external_id,
            "action_type": action.action_type,
            "params": action.params,
            "summary": action.summary,
            "status": action.status,
            "created_at": action.created_at,
        }

    @staticmethod
    def _extract_amount(text: str) -> int | None:
        m = re.search(r"(\d+(?:\.\d+)?)\s*万\s*円?", text)
        if m:
            return int(float(m.group(1)) * 10_000)
        m = re.search(r"(\d+(?:\.\d+)?)\s*千\s*円?", text)
        if m:
            return int(float(m.group(1)) * 1_000)
        m = re.search(r"(\d[\d,]*)\s*円", text)
        if m:
            return int(m.group(1).replace(",", ""))
        m = re.search(r"¥\s*(\d[\d,]*)", text)
        if m:
            return int(m.group(1).replace(",", ""))
        m = re.search(r"(\d[\d,]*)\s*yen", text, re.I)
        if m:
            return int(m.group(1).replace(",", ""))
        return None


finance_toolkit = FinanceToolkit()
