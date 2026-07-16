from app.finance.tools import FinanceToolkit


def test_balance_check():
    tk = FinanceToolkit()
    plan = tk.parse_operation("残高を教えて", "user-a")
    assert plan["action_type"] == "check_balance"
    assert plan["needs_confirmation"] is False
    assert "普通預金" in plan["message"]


def test_transfer_draft_man_yen():
    tk = FinanceToolkit()
    plan = tk.parse_operation("太郎に3万円振り込んで", "user-a")
    assert plan["action_type"] == "transfer"
    assert plan["needs_confirmation"] is True
    assert plan["pending_action"]["params"]["amount"] == 30000
    assert plan["pending_action"]["params"]["to"] == "太郎"


def test_confirm_transfer_updates_balance():
    tk = FinanceToolkit()
    plan = tk.parse_operation("花子へ1000円振り込みたい", "user-b")
    action_id = plan["pending_action"]["action_id"]
    before = tk.get_balances("user-b")["total_balance"]
    result = tk.confirm(action_id)
    assert result["ok"] is True
    after = tk.get_balances("user-b")["total_balance"]
    assert after == before - 1000
