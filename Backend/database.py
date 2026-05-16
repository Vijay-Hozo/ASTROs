"""
database.py — SQLite setup using aiosqlite.
Single file database, no server needed.
"""

import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "database.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Create all tables on startup if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS rules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_text   TEXT NOT NULL,
                parsed_json TEXT NOT NULL,
                rule_type   TEXT,
                severity    TEXT DEFAULT 'error',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT,
                xml_content TEXT NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS validation_results (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id  INTEGER,
                rule_id     INTEGER,
                rule_text   TEXT,
                status      TEXT NOT NULL,
                message     TEXT,
                rule_type   TEXT,
                validated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id),
                FOREIGN KEY (rule_id)    REFERENCES rules(id)
            );
        """)
        await db.commit()
    print(f"✅ Database initialised at {DB_PATH}")