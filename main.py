"""
Main FastAPI Web Application for VibeSplit.
Includes REST APIs, JWT Auth, Granular Permissions (Creator-only settle/delete),
AI Services, and Static Web App mounting.
"""
import os
import aiosqlite
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from datetime import datetime, timedelta
from backend.database import init_db, get_db, DB_PATH
from backend.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from backend.models import (
    SendOTPRequest, VerifyOTPRequest, OTPResponse,
    UserCreate, UserLogin, UserProfileUpdate, UserResponse, TokenResponse,
    GroupCreate, GroupMemberAdd, GroupMemberResponse, GroupResponse,
    ExpenseCreate, ExpenseResponse, ExpenseSplitResponse, ReactionResponse,
    SettlementCreate, SettlementResponse, SettleSplitRequest,
    NLPParseRequest, NLPParseResponse,
    RoastRequest, RoastResponse,
    ReceiptScanRequest, ReceiptScanResponse,
    GroupVibeCheckResponse
)
from backend.email_service import generate_otp_code, send_verification_email_async, SMTP_HOST, RESEND_API_KEY
from backend.debt_engine import compute_group_balances
from backend.ai_service import AIService

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    await init_db()
    yield

app = FastAPI(
    title="VibeSplit API",
    description="AI-Powered Gen-Z Group Expense Splitter & Settlement Web App",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# AUTHENTICATION & EMAIL OTP VERIFICATION APIS
# ==========================================

@app.post("/api/auth/send-otp", response_model=OTPResponse)
async def send_otp(req: SendOTPRequest, db: aiosqlite.Connection = Depends(get_db)):
    email_clean = req.email.lower().strip()
    
    # Check if already registered
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="This email is already registered. Please sign in instead.")

    otp = generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    await db.execute("""
        INSERT INTO email_otps (email, otp_code, expires_at, is_used)
        VALUES (?, ?, ?, 0)
    """, (email_clean, otp, expires_at.strftime("%Y-%m-%d %H:%M:%S")))
    await db.commit()

    # Dispatch email async
    await send_verification_email_async(email_clean, otp, req.full_name or "Friend")

    return {
        "message": f"Verification code sent to {email_clean}",
        "email": email_clean,
        "dev_otp": otp if (not SMTP_HOST and not RESEND_API_KEY) else None
    }

@app.post("/api/auth/verify-otp")
async def verify_otp(req: VerifyOTPRequest, db: aiosqlite.Connection = Depends(get_db)):
    email_clean = req.email.lower().strip()
    cursor = await db.execute("""
        SELECT * FROM email_otps
        WHERE email = ? AND otp_code = ? AND is_used = 0 AND expires_at >= CURRENT_TIMESTAMP
        ORDER BY created_at DESC LIMIT 1
    """, (email_clean, req.otp_code.strip()))
    otp_record = await cursor.fetchone()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code. Please check your email or request a new code.")

    return {"message": "Verification code confirmed! ✨", "email": email_clean, "valid": True}

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_in: UserCreate, db: aiosqlite.Connection = Depends(get_db)):
    username_clean = user_in.username.lower().strip()
    email_clean = user_in.email.lower().strip()

    # 1. Check uniqueness
    cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username_clean,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail=f"Username '@{username_clean}' is already taken.")

    cursor = await db.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Email is already registered.")

    # 2. Check OTP verification if provided
    if user_in.otp_code:
        cursor = await db.execute("""
            SELECT id FROM email_otps
            WHERE email = ? AND otp_code = ? AND is_used = 0
            ORDER BY created_at DESC LIMIT 1
        """, (email_clean, user_in.otp_code.strip()))
        otp_rec = await cursor.fetchone()
        if not otp_rec:
            raise HTTPException(status_code=400, detail="Invalid or expired verification code.")
        await db.execute("UPDATE email_otps SET is_used = 1 WHERE id = ?", (otp_rec["id"],))

    pwd_hash = get_password_hash(user_in.password)
    avatar = user_in.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={username_clean}"
    persona = user_in.persona or "Boba Baron 🧋"

    cursor = await db.execute("""
        INSERT INTO users (username, email, password_hash, full_name, avatar_url, persona, payment_handle, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (username_clean, email_clean, pwd_hash, user_in.full_name, avatar, persona, user_in.payment_handle or ""))
    await db.commit()
    user_id = cursor.lastrowid

    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    new_user = dict(await cursor.fetchone())

    token = create_access_token({"sub": str(user_id), "username": new_user["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {**new_user, "created_at": str(new_user["created_at"])}
    }

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(login_in: UserLogin, db: aiosqlite.Connection = Depends(get_db)):
    identifier = login_in.username_or_email.lower()
    cursor = await db.execute("SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier))
    user = await cursor.fetchone()
    if not user or not verify_password(login_in.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid username/email or password")

    user_dict = dict(user)
    token = create_access_token({"sub": str(user_dict["id"]), "username": user_dict["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {**user_dict, "created_at": str(user_dict["created_at"])}
    }

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return {**current_user, "created_at": str(current_user["created_at"])}

@app.put("/api/auth/profile", response_model=UserResponse)
async def update_profile(profile_in: UserProfileUpdate, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    full_name = profile_in.full_name if profile_in.full_name is not None else current_user["full_name"]
    avatar = profile_in.avatar_url if profile_in.avatar_url is not None else current_user["avatar_url"]
    persona = profile_in.persona if profile_in.persona is not None else current_user["persona"]
    payment_handle = profile_in.payment_handle if profile_in.payment_handle is not None else current_user["payment_handle"]

    await db.execute("""
        UPDATE users
        SET full_name = ?, avatar_url = ?, persona = ?, payment_handle = ?
        WHERE id = ?
    """, (full_name, avatar, persona, payment_handle, current_user["id"]))
    await db.commit()

    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],))
    updated = dict(await cursor.fetchone())
    return {**updated, "created_at": str(updated["created_at"])}

@app.get("/api/users/search")
async def search_users(q: str = Query(..., min_length=1), current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    search_term = f"%{q.lower()}%"
    cursor = await db.execute("""
        SELECT id, username, full_name, avatar_url, persona, payment_handle
        FROM users
        WHERE (LOWER(username) LIKE ? OR LOWER(email) LIKE ? OR LOWER(full_name) LIKE ?)
        LIMIT 10
    """, (search_term, search_term, search_term))
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# ==========================================
# GROUP MANAGEMENT APIS
# ==========================================

@app.post("/api/groups", response_model=GroupResponse)
async def create_group(group_in: GroupCreate, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("""
        INSERT INTO groups (name, description, emoji, theme_color, created_by_user_id)
        VALUES (?, ?, ?, ?, ?)
    """, (group_in.name, group_in.description or "", group_in.emoji or "🏖️", group_in.theme_color or "violet", current_user["id"]))
    group_id = cursor.lastrowid

    # Add creator as admin member
    await db.execute("""
        INSERT INTO group_members (group_id, user_id, role)
        VALUES (?, ?, 'admin')
    """, (group_id, current_user["id"]))

    # Add any initial members
    for uid in (group_in.initial_member_ids or []):
        if uid != current_user["id"]:
            await db.execute("""
                INSERT OR IGNORE INTO group_members (group_id, user_id, role)
                VALUES (?, ?, 'member')
            """, (group_id, uid))

    await db.commit()

    cursor = await db.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
    new_group = dict(await cursor.fetchone())
    return {
        **new_group,
        "created_at": str(new_group["created_at"]),
        "member_count": 1 + len(group_in.initial_member_ids or []),
        "total_expense": 0.0,
        "user_net_balance": 0.0
    }

@app.get("/api/groups", response_model=List[GroupResponse])
async def list_user_groups(current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("""
        SELECT g.*,
            (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count,
            (SELECT COALESCE(SUM(amount), 0.0) FROM expenses WHERE group_id = g.id) as total_expense
        FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id = ?
        ORDER BY g.created_at DESC
    """, (current_user["id"],))
    groups = [dict(r) for r in await cursor.fetchall()]

    result = []
    for g in groups:
        # compute user's net balance in this group
        balances_data = await compute_group_balances(db, g["id"])
        user_bal = next((b["net_balance"] for b in balances_data["balances"] if b["user_id"] == current_user["id"]), 0.0)
        result.append({
            **g,
            "created_at": str(g["created_at"]),
            "user_net_balance": user_bal
        })
    return result

@app.get("/api/groups/{group_id}/members", response_model=List[GroupMemberResponse])
async def get_group_members(group_id: int, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    # Check if user is member
    cursor = await db.execute("SELECT id FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, current_user["id"]))
    if not await cursor.fetchone():
        raise HTTPException(status_code=403, detail="Not a member of this group")

    cursor = await db.execute("""
        SELECT gm.role, gm.joined_at, u.id as user_id, u.username, u.full_name, u.avatar_url, u.persona, u.payment_handle
        FROM group_members gm
        JOIN users u ON gm.user_id = u.id
        WHERE gm.group_id = ?
        ORDER BY gm.role DESC, u.full_name ASC
    """, (group_id,))
    rows = [dict(r) for r in await cursor.fetchall()]
    return [{**r, "joined_at": str(r["joined_at"])} for r in rows]

@app.post("/api/groups/{group_id}/members")
async def add_group_member(group_id: int, member_in: GroupMemberAdd, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    # Check group exists
    cursor = await db.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
    group = await cursor.fetchone()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Find user by username or email
    search = member_in.username_or_email.lower().strip()
    cursor = await db.execute("SELECT id, username, full_name FROM users WHERE username = ? OR email = ?", (search, search))
    target_user = await cursor.fetchone()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User '{member_in.username_or_email}' not found")

    target_user_id = target_user["id"]

    # Check if already member
    cursor = await db.execute("SELECT id FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, target_user_id))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="User is already a member of this group")

    # Check if invitation already pending
    cursor = await db.execute("SELECT id FROM group_invitations WHERE group_id = ? AND invitee_user_id = ? AND status = 'pending'", (group_id, target_user_id))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="An invitation is already pending for this user")

    # Record pending invitation for invitee
    await db.execute("""
        INSERT INTO group_invitations (group_id, inviter_user_id, invitee_user_id, status)
        VALUES (?, ?, ?, 'pending')
    """, (group_id, current_user["id"], target_user_id))

    await db.execute("""
        INSERT INTO activity_logs (group_id, user_id, action_type, description)
        VALUES (?, ?, 'member_invited', ?)
    """, (group_id, current_user["id"], f"{current_user['full_name']} sent a group invitation to {target_user['full_name']} (@{target_user['username']})"))

    await db.commit()
    return {"message": f"Invitation sent to {target_user['full_name']}", "user_id": target_user_id}


# ==========================================
# GROUP INVITATIONS & NOTIFICATIONS APIS
# ==========================================

@app.get("/api/invitations")
async def get_my_invitations(current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("""
        SELECT gi.id, gi.group_id, gi.status, gi.created_at,
               g.name as group_name, g.emoji as group_emoji, g.description as group_description,
               u.username as inviter_username, u.full_name as inviter_name, u.avatar_url as inviter_avatar,
               u.persona as inviter_persona
        FROM group_invitations gi
        JOIN groups g ON gi.group_id = g.id
        JOIN users u ON gi.inviter_user_id = u.id
        WHERE gi.invitee_user_id = ? AND gi.status = 'pending'
        ORDER BY gi.created_at DESC
    """, (current_user["id"],))
    rows = [dict(r) for r in await cursor.fetchall()]
    return [{**r, "created_at": str(r["created_at"])} for r in rows]

@app.post("/api/invitations/{invite_id}/respond")
async def respond_to_invitation(invite_id: int, payload: dict, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    action = payload.get("action", "accept")  # "accept" or "decline"
    cursor = await db.execute("SELECT * FROM group_invitations WHERE id = ? AND invitee_user_id = ?", (invite_id, current_user["id"]))
    invitation = await cursor.fetchone()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found or not addressed to you")

    if action == "accept":
        await db.execute("""
            INSERT OR IGNORE INTO group_members (group_id, user_id, role)
            VALUES (?, ?, 'member')
        """, (invitation["group_id"], current_user["id"]))
        
        await db.execute("UPDATE group_invitations SET status = 'accepted' WHERE id = ?", (invite_id,))
        
        cursor_g = await db.execute("SELECT name FROM groups WHERE id = ?", (invitation["group_id"],))
        group = await cursor_g.fetchone()
        group_name = group["name"] if group else "Group"

        await db.execute("""
            INSERT INTO activity_logs (group_id, user_id, action_type, description)
            VALUES (?, ?, 'member_joined', ?)
        """, (invitation["group_id"], current_user["id"], f"{current_user['full_name']} accepted invite and joined '{group_name}' 🎉"))

        await db.commit()
        return {"message": f"You joined '{group_name}'! 🚀", "group_id": invitation["group_id"], "status": "accepted"}
    else:
        await db.execute("UPDATE group_invitations SET status = 'declined' WHERE id = ?", (invite_id,))
        await db.commit()
        return {"message": "Invitation declined", "status": "declined"}



# ==========================================
# EXPENSE MANAGEMENT & STRICT PERMISSIONS
# ==========================================

@app.get("/api/groups/{group_id}/expenses", response_model=List[ExpenseResponse])
async def list_expenses(group_id: int, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    # Verify group membership
    cursor = await db.execute("SELECT id FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, current_user["id"]))
    if not await cursor.fetchone():
        raise HTTPException(status_code=403, detail="Not authorized to view this group's expenses")

    cursor = await db.execute("""
        SELECT e.*,
            uc.username as creator_username, uc.full_name as creator_name,
            up.username as payer_username, up.full_name as payer_name
        FROM expenses e
        JOIN users uc ON e.created_by_user_id = uc.id
        JOIN users up ON e.paid_by_user_id = up.id
        WHERE e.group_id = ?
        ORDER BY e.created_at DESC
    """, (group_id,))
    expenses = [dict(r) for r in await cursor.fetchall()]

    result = []
    for exp in expenses:
        exp_id = exp["id"]
        # Fetch splits
        cursor_s = await db.execute("""
            SELECT es.*, u.username, u.full_name, u.avatar_url,
                   us.full_name as settler_name
            FROM expense_splits es
            JOIN users u ON es.user_id = u.id
            LEFT JOIN users us ON es.settled_by_user_id = us.id
            WHERE es.expense_id = ?
        """, (exp_id,))
        splits = [dict(s) for s in await cursor_s.fetchall()]

        # Fetch reactions
        cursor_r = await db.execute("""
            SELECT r.emoji, u.username
            FROM reactions r
            JOIN users u ON r.user_id = u.id
            WHERE r.expense_id = ?
        """, (exp_id,))
        reaction_rows = await cursor_r.fetchall()
        
        reaction_dict = {}
        for row in reaction_rows:
            em = row["emoji"]
            if em not in reaction_dict:
                reaction_dict[em] = []
            reaction_dict[em].append(row["username"])

        reactions = [
            {"emoji": em, "count": len(usrs), "users": usrs}
            for em, usrs in reaction_dict.items()
        ]

        # STRICT ACCESS FLAG:
        # Only the person who created/added the expense (or paid) has permission to manage/delete/settle it
        can_manage = (exp["created_by_user_id"] == current_user["id"] or exp["paid_by_user_id"] == current_user["id"])

        result.append({
            **exp,
            "created_at": str(exp["created_at"]),
            "can_manage": can_manage,
            "splits": [{
                **s,
                "is_settled": bool(s["is_settled"]),
                "settled_at": str(s["settled_at"]) if s["settled_at"] else None
            } for s in splits],
            "reactions": reactions
        })

    return result

@app.post("/api/expenses", response_model=ExpenseResponse)
async def create_expense(expense_in: ExpenseCreate, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    # Check group membership
    cursor = await db.execute("SELECT id FROM group_members WHERE group_id = ? AND user_id = ?", (expense_in.group_id, current_user["id"]))
    if not await cursor.fetchone():
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    # Insert Expense record
    cursor = await db.execute("""
        INSERT INTO expenses (group_id, title, description, category, amount, currency, created_by_user_id, paid_by_user_id, split_type, receipt_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        expense_in.group_id,
        expense_in.title,
        expense_in.description or "",
        expense_in.category or "food",
        expense_in.amount,
        expense_in.currency or "₹",
        current_user["id"],  # Creator is always authenticated current_user
        expense_in.paid_by_user_id,
        expense_in.split_type or "equal",
        expense_in.receipt_url or ""
    ))
    expense_id = cursor.lastrowid

    # Insert Splits
    for sp in expense_in.splits:
        # If the debtor is the payer themselves, their split is auto-marked as settled (self-settled)
        is_self = (sp.user_id == expense_in.paid_by_user_id)
        is_settled = 1 if is_self else 0
        settled_by = current_user["id"] if is_self else None
        await db.execute("""
            INSERT INTO expense_splits (expense_id, user_id, owed_amount, split_value, is_settled, settled_by_user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (expense_id, sp.user_id, sp.owed_amount, sp.split_value or 1.0, is_settled, settled_by))

    # Activity Log
    await db.execute("""
        INSERT INTO activity_logs (group_id, user_id, action_type, description)
        VALUES (?, ?, 'expense_added', ?)
    """, (
        expense_in.group_id,
        current_user["id"],
        f"{current_user['full_name']} added expense \"{expense_in.title}\" ({expense_in.currency or '₹'}{expense_in.amount:,.2f})"
    ))

    await db.commit()

    # Return full expense detail
    cursor = await db.execute("""
        SELECT e.*,
            uc.username as creator_username, uc.full_name as creator_name,
            up.username as payer_username, up.full_name as payer_name
        FROM expenses e
        JOIN users uc ON e.created_by_user_id = uc.id
        JOIN users up ON e.paid_by_user_id = up.id
        WHERE e.id = ?
    """, (expense_id,))
    exp = dict(await cursor.fetchone())

    cursor_s = await db.execute("""
        SELECT es.*, u.username, u.full_name, u.avatar_url,
               us.full_name as settler_name
        FROM expense_splits es
        JOIN users u ON es.user_id = u.id
        LEFT JOIN users us ON es.settled_by_user_id = us.id
        WHERE es.expense_id = ?
    """, (expense_id,))
    splits = [dict(s) for s in await cursor_s.fetchall()]

    return {
        **exp,
        "created_at": str(exp["created_at"]),
        "can_manage": True,
        "splits": [{
            **s,
            "is_settled": bool(s["is_settled"]),
            "settled_at": str(s["settled_at"]) if s["settled_at"] else None
        } for s in splits],
        "reactions": []
    }

@app.delete("/api/expenses/{expense_id}")
async def delete_expense(expense_id: int, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    """
    STRICT ACCESS CONTROL RULE:
    Only the person who created/added the expense is allowed to delete it from the group.
    """
    cursor = await db.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    exp = await cursor.fetchone()
    if not exp:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Strict check: creator only
    if exp["created_by_user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Access Denied: Only the person who created/added this expense is authorized to delete it."
        )

    await db.execute("""
        INSERT INTO activity_logs (group_id, user_id, action_type, description)
        VALUES (?, ?, 'expense_deleted', ?)
    """, (exp["group_id"], current_user["id"], f"{current_user['full_name']} deleted expense \"{exp['title']}\""))

    await db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    await db.commit()
    return {"message": "Expense successfully deleted", "expense_id": expense_id}

@app.post("/api/expenses/{expense_id}/settle-split")
async def settle_expense_split(expense_id: int, settle_req: SettleSplitRequest, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    """
    STRICT ACCESS CONTROL RULE:
    Only the person who added/paid the expense is allowed to mark/settle payments received.
    """
    cursor = await db.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    exp = await cursor.fetchone()
    if not exp:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Strict check: creator or payer only
    if exp["created_by_user_id"] != current_user["id"] and exp["paid_by_user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Access Denied: Only the person who added this expense (or the payer) can settle debtor payments."
        )

    # Check split row
    cursor_s = await db.execute("SELECT * FROM expense_splits WHERE expense_id = ? AND user_id = ?", (expense_id, settle_req.user_id))
    split = await cursor_s.fetchone()
    if not split:
        raise HTTPException(status_code=404, detail="Split debtor record not found")

    new_settled_status = 0 if split["is_settled"] else 1
    await db.execute("""
        UPDATE expense_splits
        SET is_settled = ?,
            settled_at = CURRENT_TIMESTAMP,
            settled_by_user_id = ?
        WHERE expense_id = ? AND user_id = ?
    """, (new_settled_status, current_user["id"] if new_settled_status else None, expense_id, settle_req.user_id))

    # Activity log
    action_text = "marked as settled" if new_settled_status else "reopened debt for"
    cursor_u = await db.execute("SELECT full_name FROM users WHERE id = ?", (settle_req.user_id,))
    debtor = await cursor_u.fetchone()
    debtor_name = debtor["full_name"] if debtor else "member"

    await db.execute("""
        INSERT INTO activity_logs (group_id, user_id, action_type, description)
        VALUES (?, ?, 'split_settled', ?)
    """, (exp["group_id"], current_user["id"], f"{current_user['full_name']} {action_text} {debtor_name}'s share in \"{exp['title']}\""))

    await db.commit()
    return {
        "message": f"Split {'settled' if new_settled_status else 'unsettled'} successfully",
        "is_settled": bool(new_settled_status)
    }

@app.post("/api/expenses/{expense_id}/react")
async def react_to_expense(expense_id: int, payload: dict, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    emoji = payload.get("emoji", "🔥")
    # Check if already reacted with this emoji
    cursor = await db.execute("SELECT id FROM reactions WHERE expense_id = ? AND user_id = ? AND emoji = ?", (expense_id, current_user["id"], emoji))
    existing = await cursor.fetchone()
    if existing:
        # Remove reaction (toggle)
        await db.execute("DELETE FROM reactions WHERE id = ?", (existing["id"],))
        action = "removed"
    else:
        await db.execute("INSERT INTO reactions (expense_id, user_id, emoji) VALUES (?, ?, ?)", (expense_id, current_user["id"], emoji))
        action = "added"
    await db.commit()
    return {"status": "ok", "action": action, "emoji": emoji}


# ==========================================
# BALANCES & SETTLEMENTS APIS
# ==========================================

@app.get("/api/groups/{group_id}/balances")
async def get_balances(group_id: int, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    # Check membership
    cursor = await db.execute("SELECT id FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, current_user["id"]))
    if not await cursor.fetchone():
        raise HTTPException(status_code=403, detail="Not authorized for this group")

    balances_data = await compute_group_balances(db, group_id)
    return balances_data

@app.post("/api/settlements", response_model=SettlementResponse)
async def record_direct_settlement(settle_in: SettlementCreate, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    # Check membership
    cursor = await db.execute("SELECT id FROM group_members WHERE group_id = ? AND user_id = ?", (settle_in.group_id, current_user["id"]))
    if not await cursor.fetchone():
        raise HTTPException(status_code=403, detail="Not a member of this group")

    from_user_id = current_user["id"]
    cursor = await db.execute("""
        INSERT INTO settlements (group_id, from_user_id, to_user_id, amount, currency, payment_method, notes, created_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        settle_in.group_id,
        from_user_id,
        settle_in.to_user_id,
        settle_in.amount,
        settle_in.currency or "₹",
        settle_in.payment_method or "upi",
        settle_in.notes or "",
        current_user["id"]
    ))
    settle_id = cursor.lastrowid

    # Activity Log
    cursor_to = await db.execute("SELECT full_name FROM users WHERE id = ?", (settle_in.to_user_id,))
    to_user = await cursor_to.fetchone()
    to_name = to_user["full_name"] if to_user else "User"

    await db.execute("""
        INSERT INTO activity_logs (group_id, user_id, action_type, description)
        VALUES (?, ?, 'settlement_recorded', ?)
    """, (
        settle_in.group_id,
        current_user["id"],
        f"{current_user['full_name']} sent {settle_in.currency or '₹'}{settle_in.amount:,.2f} settlement to {to_name} via {settle_in.payment_method.upper()}"
    ))

    await db.commit()

    cursor_full = await db.execute("""
        SELECT s.*,
            uf.username as from_username, uf.full_name as from_name,
            ut.username as to_username, ut.full_name as to_name
        FROM settlements s
        JOIN users uf ON s.from_user_id = uf.id
        JOIN users ut ON s.to_user_id = ut.id
        WHERE s.id = ?
    """, (settle_id,))
    res = dict(await cursor_full.fetchone())
    return {**res, "created_at": str(res["created_at"])}

@app.get("/api/groups/{group_id}/activity")
async def get_activity(group_id: int, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("""
        SELECT a.*, u.username, u.full_name, u.avatar_url
        FROM activity_logs a
        JOIN users u ON a.user_id = u.id
        WHERE a.group_id = ?
        ORDER BY a.created_at DESC
        LIMIT 30
    """, (group_id,))
    rows = [dict(r) for r in await cursor.fetchall()]
    return [{**r, "created_at": str(r["created_at"])} for r in rows]


# ==========================================
# 🤖 "AMAZING AI" GEN-Z SUITE APIS
# ==========================================

@app.post("/api/ai/nlp-parse", response_model=NLPParseResponse)
async def ai_nlp_parse_expense(req: NLPParseRequest, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    """
    AI Natural Language Expense Splitter.
    Converts sentences like 'Dhairya paid 1500 for drinks with Alex and Sam' into structured data.
    """
    # Fetch group members
    cursor = await db.execute("""
        SELECT u.id as user_id, u.username, u.full_name
        FROM group_members gm
        JOIN users u ON gm.user_id = u.id
        WHERE gm.group_id = ?
    """, (req.group_id,))
    members = [dict(r) for r in await cursor.fetchall()]
    
    parsed = AIService.parse_natural_language_expense(req.prompt, members)
    return parsed

@app.post("/api/ai/roast-nudge", response_model=RoastResponse)
async def ai_generate_roast_nudge(req: RoastRequest, current_user: dict = Depends(get_current_user)):
    """
    Generates Gen-Z Debt Roaster & Nudge messages with WhatsApp / Telegram share links.
    """
    roast_data = AIService.generate_roast_nudge(
        debtor_name=req.debtor_name,
        creditor_name=req.creditor_name,
        amount=req.amount,
        currency=req.currency,
        expense_title=req.expense_title,
        tone=req.tone,
        payment_handle=req.payment_handle or ""
    )
    return roast_data

@app.post("/api/ai/receipt-scan", response_model=ReceiptScanResponse)
async def ai_receipt_scan(req: ReceiptScanRequest, current_user: dict = Depends(get_current_user)):
    """
    AI Smart Bill / Receipt Scanner.
    """
    raw = req.raw_text or "Cafe Coffee Day\n2x Boba Tea 480.00\n1x Truffle Fries 320.00\n1x Woodfired Pizza 550.00\nGST 5% 67.50\nTotal 1417.50"
    parsed_receipt = AIService.scan_receipt_text(raw)
    return parsed_receipt

@app.get("/api/groups/{group_id}/vibe-check", response_model=GroupVibeCheckResponse)
async def ai_group_vibe_check(group_id: int, current_user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)):
    """
    Group Spending Vibe Check & Gen-Z Badges.
    """
    cursor = await db.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
    grp = await cursor.fetchone()
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found")

    # Fetch expenses & balances
    cursor_e = await db.execute("SELECT * FROM expenses WHERE group_id = ?", (group_id,))
    expenses = [dict(r) for r in await cursor_e.fetchall()]

    balances_data = await compute_group_balances(db, group_id)
    vibe = AIService.generate_group_vibe_check(grp["name"], expenses, balances_data["balances"])
    vibe["group_id"] = group_id
    return vibe


# ==========================================
# STATIC FRONTEND & SPA SERVING WITH ROBUST MIME TYPES
# ==========================================

import mimetypes
mimetypes.init()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".json")

def get_file_media_type(filepath: str) -> Optional[str]:
    ext = os.path.splitext(filepath)[1].lower()
    mapping = {
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".htm": "text/html",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".ico": "image/x-icon",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
        ".ttf": "font/ttf",
    }
    return mapping.get(ext) or mimetypes.guess_type(filepath)[0] or "application/octet-stream"

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Check if requested static file exists in frontend dir
    file_path = os.path.join(FRONTEND_DIR, full_path)
    if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
        media_type = get_file_media_type(file_path)
        return FileResponse(file_path, media_type=media_type)
    
    # Default to index.html for SPA routing
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return JSONResponse({"message": "VibeSplit Backend is running. Frontend initializing..."})
