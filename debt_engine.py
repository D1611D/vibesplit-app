"""
Debt Simplification and Balance Calculation Engine.
Uses a greedy bipartite matching / graph minimization algorithm to reduce N-way circular debts.
"""
from typing import List, Dict, Any
import aiosqlite

async def compute_group_balances(db: aiosqlite.Connection, group_id: int) -> Dict[str, Any]:
    """
    Computes:
    1. Member raw balances (total_paid, total_owed, net_balance).
    2. Pairwise direct debts (who owes whom based on unsettled splits & settlements).
    3. Simplified minimum cash transactions (Splitwise algorithm).
    """
    # 1. Fetch all members
    cursor = await db.execute("""
        SELECT u.id, u.username, u.full_name, u.avatar_url, u.persona, u.payment_handle
        FROM group_members gm
        JOIN users u ON gm.user_id = u.id
        WHERE gm.group_id = ?
    """, (group_id,))
    members = [dict(row) for row in await cursor.fetchall()]
    
    member_map = {m["id"]: m for m in members}
    if not member_map:
        return {"balances": [], "simplified_debts": [], "total_spent": 0.0}

    # Initialize net balances and stats
    net_balances: Dict[int, float] = {m["id"]: 0.0 for m in members}
    total_paid: Dict[int, float] = {m["id"]: 0.0 for m in members}
    total_owed: Dict[int, float] = {m["id"]: 0.0 for m in members}
    total_group_spent: float = 0.0

    # 2. Fetch all expenses for this group
    cursor = await db.execute("""
        SELECT e.id, e.amount, e.paid_by_user_id
        FROM expenses e
        WHERE e.group_id = ?
    """, (group_id,))
    expenses = await cursor.fetchall()

    for exp in expenses:
        exp_id = exp["id"]
        payer_id = exp["paid_by_user_id"]
        amount = exp["amount"]
        total_group_spent += amount
        if payer_id in total_paid:
            total_paid[payer_id] += amount

        # Fetch splits for this expense
        cursor_splits = await db.execute("""
            SELECT user_id, owed_amount, is_settled
            FROM expense_splits
            WHERE expense_id = ?
        """, (exp_id,))
        splits = await cursor_splits.fetchall()

        for split in splits:
            u_id = split["user_id"]
            owed = split["owed_amount"]
            is_settled = split["is_settled"]
            
            if u_id in total_owed:
                total_owed[u_id] += owed

            # If NOT settled, it directly affects current net balance
            if not is_settled:
                if u_id in net_balances:
                    net_balances[u_id] -= owed
                if payer_id in net_balances:
                    net_balances[payer_id] += owed

    # 3. Fetch direct settlements made in this group
    cursor_settle = await db.execute("""
        SELECT from_user_id, to_user_id, amount
        FROM settlements
        WHERE group_id = ?
    """, (group_id,))
    settlements = await cursor_settle.fetchall()

    for s in settlements:
        from_id = s["from_user_id"]
        to_id = s["to_user_id"]
        s_amt = s["amount"]
        if from_id in net_balances:
            net_balances[from_id] += s_amt  # debtor paid money, so debt reduced (net increased)
        if to_id in net_balances:
            net_balances[to_id] -= s_amt  # creditor received money, so claim reduced (net decreased)

    # 4. Construct user balance objects
    user_balances = []
    for m in members:
        uid = m["id"]
        user_balances.append({
            "user_id": uid,
            "username": m["username"],
            "full_name": m["full_name"],
            "avatar_url": m["avatar_url"],
            "persona": m["persona"],
            "payment_handle": m["payment_handle"],
            "total_paid": round(total_paid.get(uid, 0.0), 2),
            "total_owed": round(total_owed.get(uid, 0.0), 2),
            "net_balance": round(net_balances.get(uid, 0.0), 2)
        })

    # 5. Greedy Minimized Debt Algorithm
    # Separate into debtors (net < -0.01) and creditors (net > 0.01)
    debtors = []   # list of [user_id, abs_amount_owed]
    creditors = [] # list of [user_id, amount_to_receive]

    for uid, net in net_balances.items():
        rounded_net = round(net, 2)
        if rounded_net < -0.01:
            debtors.append({"id": uid, "amount": -rounded_net})
        elif rounded_net > 0.01:
            creditors.append({"id": uid, "amount": rounded_net})

    simplified_debts = []
    
    # Sort descending by amount
    debtors.sort(key=lambda x: x["amount"], reverse=True)
    creditors.sort(key=lambda x: x["amount"], reverse=True)

    d_idx = 0
    c_idx = 0

    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor = debtors[d_idx]
        creditor = creditors[c_idx]

        settle_amt = min(debtor["amount"], creditor["amount"])
        settle_amt = round(settle_amt, 2)

        if settle_amt > 0.01:
            debtor_info = member_map.get(debtor["id"], {})
            creditor_info = member_map.get(creditor["id"], {})

            simplified_debts.append({
                "from_user_id": debtor["id"],
                "from_username": debtor_info.get("username", "Unknown"),
                "from_name": debtor_info.get("full_name", "Unknown"),
                "to_user_id": creditor["id"],
                "to_username": creditor_info.get("username", "Unknown"),
                "to_name": creditor_info.get("full_name", "Unknown"),
                "to_payment_handle": creditor_info.get("payment_handle", ""),
                "amount": settle_amt,
                "currency": "₹"
            })

        debtor["amount"] -= settle_amt
        creditor["amount"] -= settle_amt

        if debtor["amount"] < 0.01:
            d_idx += 1
        if creditor["amount"] < 0.01:
            c_idx += 1

    return {
        "balances": user_balances,
        "simplified_debts": simplified_debts,
        "total_spent": round(total_group_spent, 2)
    }
