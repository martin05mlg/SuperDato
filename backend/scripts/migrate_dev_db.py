import sqlite3
import uuid
from datetime import datetime, timezone

def migrate():
    con = sqlite3.connect("superdato_dev.db")
    cur = con.cursor()

    tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Existing tables:", tables)

    # 1. Check users table
    if "users" in tables:
        user_cols = [r[1] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
        print("users columns:", user_cols)
        if "is_superuser" not in user_cols:
            print("Adding is_superuser to users...")
            cur.execute("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT 0 NOT NULL")
            con.commit()

        # Update dev user to superuser
        cur.execute("UPDATE users SET is_superuser = 1 WHERE email = 'dev@superdato.es'")
        con.commit()
        print("Updated dev@superdato.es to superuser.")

    # 2. Check receipts table
    if "receipts" in tables:
        receipt_cols = [r[1] for r in cur.execute("PRAGMA table_info(receipts)").fetchall()]
        print("receipts columns:", receipt_cols)
        if "assignment_status" not in receipt_cols:
            print("Adding assignment_status to receipts...")
            cur.execute("ALTER TABLE receipts ADD COLUMN assignment_status VARCHAR(30) DEFAULT 'ASSIGNED' NOT NULL")
            con.commit()

    # 3. Check registration_tokens table
    if "registration_tokens" not in tables:
        print("Creating registration_tokens table...")
        cur.execute("""
        CREATE TABLE registration_tokens (
            id CHAR(32) PRIMARY KEY,
            token VARCHAR(100) NOT NULL UNIQUE,
            note VARCHAR(255),
            max_uses INTEGER NOT NULL DEFAULT 1,
            times_used INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            expires_at DATETIME,
            created_by_user_id CHAR(32),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        """)
        con.commit()
        print("Created registration_tokens table.")

    # Seed default token
    cur.execute("SELECT id FROM registration_tokens WHERE token = 'SUP-ADMIN-2026'")
    existing_token = cur.fetchone()
    if not existing_token:
        token_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            INSERT INTO registration_tokens (id, token, note, max_uses, times_used, is_active, created_at, updated_at)
            VALUES (?, 'SUP-ADMIN-2026', 'Token inicial de pruebas', 10, 0, 1, ?, ?)
        """, (token_id, now, now))
        con.commit()
        print("Seeded default registration token: SUP-ADMIN-2026")
    else:
        print("Default token SUP-ADMIN-2026 already exists.")

    con.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()

