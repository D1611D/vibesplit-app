# ⚡ VibeSplit — Full-Stack AI Group Expense Splitter & Settlement Web App

VibeSplit is a full-stack, production-grade group expense splitting and debt settlement web application with real-time multi-computer synchronization, email OTP verification, strict access permissions, and an AI Gen-Z suite.

---

## 🗄️ 1. Where Is Your Data Stored?

All data is securely stored in a centralized database on the backend server:
- **Database File**: `vibesplit.db` (SQLite with foreign keys enabled & easy PostgreSQL upgrade support).
- **Stored Data Entities**:
  - `users`: Private user credentials with bcrypt password hashing, avatar, persona, and `is_verified` status.
  - `email_otps`: 6-digit verification codes with 10-minute expiration timestamps.
  - `groups` & `group_members`: Private groups and members.
  - `group_invitations`: Pending and accepted cross-computer invitations.
  - `expenses` & `expense_splits`: Expenses with debtor shares and settlement tracking.
  - `settlements` & `activity_logs`: UPI transactions and event logs.

---

## 🔒 2. Multi-User Isolation & Private Accounts

- **Private Dashboard**: When you sign in or create an account, you get access **only to your own private account**.
- **No Shared Unwanted Visibility**: You cannot see other users' groups or balances unless they invite you to their group and you accept the invitation.
- **Strict Access Control**: Only the creator of an expense can mark debtor splits as settled or delete the expense.

---

## 📧 3. Real Email OTP Verification

During registration, VibeSplit validates the user's email with a 6-digit verification code:
1. User enters Full Name, Username, Email, and Password $\rightarrow$ Clicks **"Send Email Verification Code 📧"**.
2. The server generates a secure 6-digit OTP code and dispatches a Gen-Z styled HTML email.
3. User enters the 6-digit code $\rightarrow$ Server verifies OTP $\rightarrow$ Account is activated and logged in with a JWT token!

> **SMTP Setup (Optional)**: To send real emails via Gmail, SendGrid, or Resend, set these environment variables:
> - `SMTP_HOST=smtp.gmail.com`
> - `SMTP_PORT=587`
> - `SMTP_USER=your_email@gmail.com`
> - `SMTP_PASSWORD=your_app_password`
> - `SMTP_FROM_EMAIL=your_email@gmail.com`
> *(If not set, the OTP is automatically logged to the server console and displayed for quick development testing)*.

---

## 👥 4. Cross-Computer Group Invitations (Multi-Device Sync)

When User A on **Computer 1** invites User B on **Computer 2**:
1. User A opens the group and clicks **"Invite Friend"** $\rightarrow$ Types User B's username or email.
2. An invitation record is stored in the central database.
3. When User B logs in from **Computer 2** (or phone), an in-app notification bell and top banner instantly alert User B:
   *"User A invited you to join Group Name!"*
4. User B clicks **"Accept & Join 🚀"** $\rightarrow$ Confetti explodes, and the group tab instantly appears on Computer 2 with live expense syncing!

---

## 🚀 5. How to Deploy to Cloud for Free (Sync Any Computer & Phone)

### 🌟 Option A: 1-Click Free Hosting on Render (Recommended)
1. Push your repository to GitHub.
2. Go to [Render.com](https://render.com) and click **New + $\rightarrow$ Web Service**.
3. Connect your GitHub repository.
4. Select:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Click **Deploy Web Service**!
6. Render will give you a free live URL (e.g. `https://vibesplit-app.onrender.com`).
7. Open this URL on **any computer or phone** to split expenses seamlessly!

---

### 💻 Option B: Run Locally on Your Machine
1. Start the backend server:
   ```bash
   python run.py
   ```
2. Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.
