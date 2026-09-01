"""
Database layer for VibeSplit using aiosqlite.
Manages database initialization, connections, tables, email OTPs, and group invitations.
"""
import os
import aiosqlite
import logging

DB_PATH = os.environ.get("VIBESPLIT_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "vibesplit.db"))
logger = logging.getLogger("vibesplit.database")

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON;")
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # 1. Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                avatar_url TEXT DEFAULT '',
                persona TEXT DEFAULT 'Boba Baron',
                payment_handle TEXT DEFAULT '',
                is_verified INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Check and add is_verified column if table already existed without it
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 1;")
            await db.commit()
        except Exception:
            pass  # Column already exists
        
        # 2. Email OTPs table (for real email verification on registration)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS email_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Groups table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                emoji TEXT DEFAULT '🚀',
                theme_color TEXT DEFAULT 'violet',
                created_by_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        
        # 4. Group Members
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        
        # 5. Group Invitations (For cross-user & multi-computer notifications)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                inviter_user_id INTEGER NOT NULL,
                invitee_user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, invitee_user_id, status),
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (inviter_user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (invitee_user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # 6. Expenses
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'food',
                amount REAL NOT NULL,
                currency TEXT DEFAULT '₹',
                created_by_user_id INTEGER NOT NULL,
                paid_by_user_id INTEGER NOT NULL,
                split_type TEXT DEFAULT 'equal',
                receipt_url TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (paid_by_user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        
        # 7. Expense Splits
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expense_splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                owed_amount REAL NOT NULL,
                split_value REAL NOT NULL,
                is_settled INTEGER DEFAULT 0,
                settled_at TIMESTAMP NULL,
                settled_by_user_id INTEGER NULL,
                UNIQUE(expense_id, user_id),
                FOREIGN KEY (expense_id) REFERENCES expenses (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (settled_by_user_id) REFERENCES users (id) ON DELETE SET NULL
            );
        """)
        
        # 8. Settlements
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT '₹',
                payment_method TEXT DEFAULT 'upi',
                notes TEXT DEFAULT '',
                created_by_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (from_user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (to_user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        
        # 9. Reactions
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(expense_id, user_id, emoji),
                FOREIGN KEY (expense_id) REFERENCES expenses (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        
        # 10. Activity logs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        
        await db.commit()
        logger.info("Database initialized successfully.")
