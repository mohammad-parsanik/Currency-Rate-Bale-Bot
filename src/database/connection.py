import aiosqlite
import logging
from src.config import settings

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def get_db_connection():
    db_dir = os.path.dirname(settings.DB_PATH)
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except PermissionError:
            logger.error(f"Permission denied: cannot create directory {db_dir}. If you are using Kubernetes, ensure your volume has the correct permissions (e.g., using securityContext fsGroup).")
            raise
        
        if not os.access(db_dir, os.W_OK):
            logger.error(f"Permission denied: directory {db_dir} is not writable. If using Kubernetes volumes, the mounted volume might be owned by root. Consider using an initContainer to change ownership or set securityContext.fsGroup.")
            raise PermissionError(f"Directory {db_dir} is not writable")

    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    logger.info("Initializing database...")
    async with get_db_connection() as db:
        await db.executescript("""
            -- Cached prices
            CREATE TABLE IF NOT EXISTS prices (
                asset_code TEXT,
                asset_name_fa TEXT NOT NULL,
                category TEXT NOT NULL,
                price TEXT NOT NULL,
                price_high TEXT,
                price_low TEXT,
                change_amount TEXT,
                change_percent REAL,
                change_direction TEXT,
                source TEXT NOT NULL,
                source_timestamp TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (asset_code, source)
            );

            -- Bot users
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                preferred_source TEXT DEFAULT 'tgju',
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- User source logs
            CREATE TABLE IF NOT EXISTS user_source_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                old_source TEXT,
                new_source TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Interaction log
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Error log
            CREATE TABLE IF NOT EXISTS fetch_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                error_message TEXT NOT NULL,
                error_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_interactions_created ON interactions(created_at);
            CREATE INDEX IF NOT EXISTS idx_interactions_command ON interactions(command);
            CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen_at);
            CREATE INDEX IF NOT EXISTS idx_fetch_errors_created ON fetch_errors(created_at);
            CREATE INDEX IF NOT EXISTS idx_user_source_logs_changed ON user_source_logs(changed_at);
        """)
        await db.commit()
    logger.info("Database initialized.")
