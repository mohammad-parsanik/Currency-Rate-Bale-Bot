"""
connection.py — Async SQLite connection factory and schema initialisation

Uses aiosqlite for non-blocking database access. WAL journal mode is
enabled on every connection to allow concurrent readers alongside the
single writer without locking.

The database file and its parent directory are created automatically
on first use. Kubernetes-specific permission error hints are included
in the error messages to aid production debugging.
"""

import aiosqlite
import logging
import os
from contextlib import asynccontextmanager
from src.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db_connection():
    """Async context manager that yields a configured aiosqlite connection.

    - Creates the parent directory of DB_PATH if it does not exist.
    - Enables WAL journal mode for better read concurrency.
    - Sets row_factory to aiosqlite.Row so rows behave like dicts.

    Usage:
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM prices")

    Raises:
        PermissionError: If the data directory cannot be created or written to.
    """
    db_dir = os.path.dirname(settings.DB_PATH)
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except PermissionError:
            logger.error(
                f"Permission denied: cannot create directory {db_dir}. "
                "If you are using Kubernetes, ensure your volume has the correct "
                "permissions (e.g., using securityContext fsGroup)."
            )
            raise

        if not os.access(db_dir, os.W_OK):
            logger.error(
                f"Permission denied: directory {db_dir} is not writable. "
                "If using Kubernetes volumes, the mounted volume might be owned by root. "
                "Consider using an initContainer to change ownership or set securityContext.fsGroup."
            )
            raise PermissionError(f"Directory {db_dir} is not writable")

    async with aiosqlite.connect(settings.DB_PATH) as db:
        # WAL mode: readers don't block writer, writer doesn't block readers.
        # Important because the scheduler writes while the bot and admin panel read.
        await db.execute("PRAGMA journal_mode=WAL")
        # Row factory: enables dict-style column access on result rows
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    """Create all database tables and indexes if they do not already exist.

    Called once at application startup (before any other service starts).
    Uses CREATE TABLE IF NOT EXISTS, so re-running is always safe.

    Tables created:
        prices           — Cached asset prices from all sources (upserted each cycle)
        users            — Registered bot users and their preferred source
        user_source_logs — Audit log of user source-preference changes
        interactions     — Every command / button press for analytics
        fetch_errors     — Errors logged when a fetch cycle fails
    """
    logger.info("Initializing database...")
    async with get_db_connection() as db:
        await db.executescript("""
            -- Cached prices: one row per (asset_code, source) pair
            CREATE TABLE IF NOT EXISTS prices (
                asset_code       TEXT,
                asset_name_fa    TEXT NOT NULL,
                category         TEXT NOT NULL,     -- 'currency' | 'gold' | 'coin'
                price            TEXT NOT NULL,     -- Current price (Toman or USD for ounce)
                price_high       TEXT,              -- 12-hour high
                price_low        TEXT,              -- 12-hour low
                change_amount    TEXT,              -- Absolute change value
                change_percent   REAL,              -- Percentage change (signed)
                change_direction TEXT,              -- 'high' | 'low' | 'stable'
                source           TEXT NOT NULL,     -- 'tgju' | 'nerkh'
                source_timestamp TEXT,              -- Timestamp reported by the source API
                fetched_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (asset_code, source)
            );

            -- Bot users: created/updated on every incoming message
            CREATE TABLE IF NOT EXISTS users (
                user_id          INTEGER PRIMARY KEY,
                first_name       TEXT,
                last_name        TEXT,
                username         TEXT,
                preferred_source TEXT DEFAULT 'tgju',  -- Last source chosen by the user
                first_seen_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Audit trail: records every time a user switches data source
            CREATE TABLE IF NOT EXISTS user_source_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                old_source TEXT,
                new_source TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Analytics: every command and inline-button press
            CREATE TABLE IF NOT EXISTS interactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                command    TEXT NOT NULL,   -- e.g. '/start', 'btn:all', 'btn:cat:gold'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Error log: fetch failures from tgju / nerkh
            CREATE TABLE IF NOT EXISTS fetch_errors (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                source        TEXT NOT NULL,
                error_message TEXT NOT NULL,
                error_type    TEXT,         -- Python exception class name
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Indexes for the most common query patterns
            CREATE INDEX IF NOT EXISTS idx_interactions_created  ON interactions(created_at);
            CREATE INDEX IF NOT EXISTS idx_interactions_command   ON interactions(command);
            CREATE INDEX IF NOT EXISTS idx_users_last_seen        ON users(last_seen_at);
            CREATE INDEX IF NOT EXISTS idx_fetch_errors_created   ON fetch_errors(created_at);
            CREATE INDEX IF NOT EXISTS idx_user_source_logs_changed ON user_source_logs(changed_at);
        """)
        await db.commit()
    logger.info("Database initialized.")
