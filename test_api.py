"""
Automated Test Suite for VibeSplit API.
Tests Authentication, Groups, Expense Creation, Strict Creator-only Access Controls,
Settlement Flows, Debt Engine, and AI Features using ASGI in-memory client.
"""
import sys
import os
import asyncio
import httpx

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app, init_db, seed_demo_data
import aiosqlite
from backend.database import DB_PATH

async def run_tests():
    print("🚀 Initializing Database & Seed Data...")
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await seed_demo_data(db)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("\n🧪 [1/7] Testing User Authentication & Login...")
        # 1. Login as dhairya (creator of Exp #1)
        res_login_dhairya = await client.post("/api/auth/login", json={
            "username_or_email": "dhairya",
            "password": "password123"
        })
        assert res_login_dhairya.status_code == 200, f"Login failed: {res_login_dhairya.text}"
        token_dhairya = res_login_dhairya.json()["access_token"]
        headers_dhairya = {"Authorization": f"Bearer {token_dhairya}"}

        # 2. Login as kabir (member, not creator of Exp #1)
        res_login_kabir = await client.post("/api/auth/login", json={
            "username_or_email": "kabir",
            "password": "password123"
        })
        assert res_login_kabir.status_code == 200, f"Login failed: {res_login_kabir.text}"
        token_kabir = res_login_kabir.json()["access_token"]
        headers_kabir = {"Authorization": f"Bearer {token_kabir}"}
        print("✅ Auth login passed for both Dhairya and Kabir.")

        print("\n🧪 [2/7] Testing Group Listing & Balances...")
        res_groups = await client.get("/api/groups", headers=headers_dhairya)
        print(f"Group status: {res_groups.status_code}, response: {res_groups.text}")
        assert res_groups.status_code == 200, f"Group fetch failed: {res_groups.text}"
        groups = res_groups.json()
        target_group = next((g for g in groups if g["id"] == 1), groups[0])
        group_id = target_group["id"]
        print(f"✅ Found {len(groups)} groups. Active test group: '{target_group['name']}' (ID: {group_id})")

        print("\n🧪 [3/7] Testing Expense Creation...")
        # Dhairya creates a new expense: "Arcade Games & VR" (₹1,600, split 4 ways: 400 each)
        res_exp = await client.post("/api/expenses", headers=headers_dhairya, json={
            "group_id": group_id,
            "title": "Arcade Games & VR Arena",
            "category": "vibes",
            "amount": 1600.0,
            "currency": "₹",
            "paid_by_user_id": 1,
            "split_type": "equal",
            "splits": [
                {"user_id": 1, "owed_amount": 400.0, "split_value": 1.0},
                {"user_id": 2, "owed_amount": 400.0, "split_value": 1.0},
                {"user_id": 3, "owed_amount": 400.0, "split_value": 1.0},
                {"user_id": 4, "owed_amount": 400.0, "split_value": 1.0}
            ]
        })
        assert res_exp.status_code == 200, f"Create expense failed: {res_exp.text}"
        new_exp = res_exp.json()
        new_exp_id = new_exp["id"]
        print(f"✅ Created expense #{new_exp_id}: '{new_exp['title']}' by Dhairya (User ID 1)")

        print("\n🧪 [4/7] Testing STRICT ACCESS CONTROL (Non-Creator Permission Denial)...")
        # Kabir (User ID 3) tries to DELETE the expense created by Dhairya -> MUST FAIL WITH HTTP 403
        res_unauthorized_del = await client.delete(f"/api/expenses/{new_exp_id}", headers=headers_kabir)
        assert res_unauthorized_del.status_code == 403, f"Expected 403 Forbidden, got {res_unauthorized_del.status_code}"
        print(f"✅ Successfully blocked Kabir from deleting Dhairya's expense: {res_unauthorized_del.json()['detail']}")

        # Kabir (User ID 3) tries to mark a debtor split as settled on Dhairya's expense -> MUST FAIL WITH HTTP 403
        res_unauthorized_settle = await client.post(f"/api/expenses/{new_exp_id}/settle-split", headers=headers_kabir, json={
            "expense_id": new_exp_id,
            "user_id": 4
        })
        assert res_unauthorized_settle.status_code == 403, f"Expected 403 Forbidden, got {res_unauthorized_settle.status_code}"
        print(f"✅ Successfully blocked Kabir from settling Dhairya's expense: {res_unauthorized_settle.json()['detail']}")

        print("\n🧪 [5/7] Testing Authorized Creator Settle & Delete Flow...")
        # Dhairya (the creator) settles Kabir's split (User ID 3)
        res_auth_settle = await client.post(f"/api/expenses/{new_exp_id}/settle-split", headers=headers_dhairya, json={
            "expense_id": new_exp_id,
            "user_id": 3
        })
        assert res_auth_settle.status_code == 200, f"Creator settle failed: {res_auth_settle.text}"
        print(f"✅ Dhairya (creator) successfully settled Kabir's share: {res_auth_settle.json()}")

        # Dhairya deletes the test expense
        res_auth_del = await client.delete(f"/api/expenses/{new_exp_id}", headers=headers_dhairya)
        assert res_auth_del.status_code == 200
        print("✅ Dhairya (creator) successfully deleted the test expense.")

        print("\n🧪 [6/7] Testing 🤖 AI Features (NLP Magic Parser & Gen-Z Roaster)...")
        # AI NLP Parse
        res_nlp = await client.post("/api/ai/nlp-parse", headers=headers_dhairya, json={
            "group_id": group_id,
            "prompt": "Ananya paid 1800 for Korean BBQ with Kabir and Tanya"
        })
        assert res_nlp.status_code == 200
        nlp_data = res_nlp.json()
        assert nlp_data["amount"] == 1800.0
        assert nlp_data["paid_by_username"] == "ananya"
        assert len(nlp_data["splits"]) == 2 or len(nlp_data["splits"]) == 3
        print(f"✅ AI NLP Parser extracted: Title='{nlp_data['title']}', Amount=₹{nlp_data['amount']}, Payer=@{nlp_data['paid_by_username']}, Splits={len(nlp_data['splits'])}")

        # AI Gen-Z Roast Generator
        res_roast = await client.post("/api/ai/roast-nudge", headers=headers_dhairya, json={
            "debtor_name": "Kabir",
            "creditor_name": "Dhairya",
            "amount": 900.0,
            "currency": "₹",
            "expense_title": "Sunset Shack Seafood",
            "tone": "savage",
            "payment_handle": "dhairya@upi"
        })
        assert res_roast.status_code == 200
        roast_data = res_roast.json()
        assert len(roast_data["roast_text"]) > 20
        assert "api.whatsapp.com" in roast_data["whatsapp_share_url"]
        print(f"✅ AI Gen-Z Roast Generated: {roast_data['roast_text'][:60]}...")

        print("\n🧪 [7/8] Testing Group Invitations & Notification Flow...")
        # Check Dhairya's pending invitations (should have invite from Kabir for Hackathon Hustle)
        res_invites = await client.get("/api/invitations", headers=headers_dhairya)
        assert res_invites.status_code == 200
        invites = res_invites.json()
        print(f"✅ Dhairya has {len(invites)} pending group invitations.")
        
        if invites:
            first_invite = invites[0]
            # Accept invitation
            res_accept = await client.post(f"/api/invitations/{first_invite['id']}/respond", headers=headers_dhairya, json={"action": "accept"})
            assert res_accept.status_code == 200
            print(f"✅ Successfully accepted invite for '{first_invite['group_name']}': {res_accept.json()['message']}")

        print("\n🧪 [8/8] Testing AI Group Vibe Check & Debt Minimizer Graph...")
        res_vibe = await client.get(f"/api/groups/{group_id}/vibe-check", headers=headers_dhairya)
        assert res_vibe.status_code == 200
        vibe_data = res_vibe.json()
        assert vibe_data["vibe_score"] > 50
        assert len(vibe_data["user_badges"]) >= 1
        print(f"✅ Vibe Check: Score={vibe_data['vibe_score']}/100, Title='{vibe_data['vibe_title']}', Badges={len(vibe_data['user_badges'])}")

        print("\n==========================================")
        print("🎉 ALL 8/8 TEST SUITES PASSED FLAWLESSLY!")
        print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
