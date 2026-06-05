"""
repositories.py — Data-access layer (Repository pattern)

Each repository class is a collection of static async methods that wrap
SQL queries for a single table. No raw SQL appears outside this module —
all other modules interact with the database through these classes.

Repositories:
    PriceRepository        — prices table
    UserRepository         — users table
    InteractionRepository  — interactions table
    ErrorRepository        — fetch_errors table
    UserSourceLogRepository — user_source_logs table
"""

import logging
from src.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class PriceRepository:
    """Data-access methods for the prices table."""

    @staticmethod
    async def upsert_many(prices: list[dict]):
        """Insert or update a batch of price records.

        Uses SQLite's INSERT … ON CONFLICT DO UPDATE (upsert) so each
        call is idempotent — running the same data twice is safe.

        Args:
            prices: List of price dicts as returned by the fetchers.
                    Must contain keys: asset_code, asset_name_fa, category,
                    price, price_high, price_low, change_amount, change_percent,
                    change_direction, source, source_timestamp.
        """
        if not prices:
            return

        async with get_db_connection() as db:
            for p in prices:
                await db.execute("""
                    INSERT INTO prices (
                        asset_code, asset_name_fa, category, price, price_high, price_low,
                        change_amount, change_percent, change_direction, source, source_timestamp, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(asset_code, source) DO UPDATE SET
                        asset_name_fa     = excluded.asset_name_fa,
                        category          = excluded.category,
                        price             = excluded.price,
                        price_high        = excluded.price_high,
                        price_low         = excluded.price_low,
                        change_amount     = excluded.change_amount,
                        change_percent    = excluded.change_percent,
                        change_direction  = excluded.change_direction,
                        source_timestamp  = excluded.source_timestamp,
                        fetched_at        = CURRENT_TIMESTAMP
                """, (
                    p['asset_code'], p['asset_name_fa'], p['category'], p['price'],
                    p['price_high'], p['price_low'], p['change_amount'], p['change_percent'],
                    p['change_direction'], p['source'], p.get('source_timestamp')
                ))
            await db.commit()

    @staticmethod
    async def get_all_prices(source: str) -> list[dict]:
        """Return all cached prices for the given source.

        Args:
            source: 'tgju' or 'nerkh'.

        Returns:
            List of price dicts (may be empty if no data has been fetched yet).
        """
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM prices WHERE source = ?", (source,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    async def get_price(asset_code: str, source: str) -> dict | None:
        """Return a single price record by asset code and source.

        Returns:
            A price dict, or None if the record does not exist.
        """
        async with get_db_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM prices WHERE asset_code = ? AND source = ?",
                (asset_code, source)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None


class UserRepository:
    """Data-access methods for the users table."""

    @staticmethod
    async def upsert_user(user_id: int, first_name: str, last_name: str, username: str):
        """Create a new user record or update the display fields of an existing one.

        preferred_source is intentionally NOT overwritten on update so that
        a user who has chosen 'nerkh' keeps that preference across sessions.
        last_seen_at is always updated to the current timestamp.
        """
        async with get_db_connection() as db:
            await db.execute("""
                INSERT INTO users (user_id, first_name, last_name, username)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name   = excluded.first_name,
                    last_name    = excluded.last_name,
                    username     = excluded.username,
                    last_seen_at = CURRENT_TIMESTAMP
            """, (user_id, first_name, last_name, username))
            await db.commit()

    @staticmethod
    async def get_user(user_id: int) -> dict | None:
        """Fetch a single user by their Bale user ID.

        Returns:
            A user dict including preferred_source, or None if not found.
        """
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def update_preferred_source(user_id: int, new_source: str):
        """Persist the user's preferred data source ('tgju' or 'nerkh')."""
        async with get_db_connection() as db:
            await db.execute(
                "UPDATE users SET preferred_source = ? WHERE user_id = ?",
                (new_source, user_id)
            )
            await db.commit()

    @staticmethod
    async def get_stats() -> dict:
        """Aggregate user statistics for the admin dashboard.

        Returns:
            Dict with keys:
                total        — total number of registered users
                active       — users who interacted within the last 24 hours
                recent_users — list of up to 50 most-recently-active users
        """
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT COUNT(*) as total FROM users")
            total = (await cursor.fetchone())['total']

            cursor = await db.execute(
                "SELECT COUNT(*) as active FROM users WHERE last_seen_at >= datetime('now', '-1 day')"
            )
            active = (await cursor.fetchone())['active']

            cursor = await db.execute(
                "SELECT * FROM users ORDER BY last_seen_at DESC LIMIT 50"
            )
            recent_users = [dict(row) for row in await cursor.fetchall()]

            return {"total": total, "active": active, "recent_users": recent_users}


class InteractionRepository:
    """Data-access methods for the interactions table."""

    @staticmethod
    async def log_interaction(user_id: int, command: str):
        """Append a new interaction record.

        Args:
            user_id: Bale user ID of the actor.
            command: The text command (e.g. '/start') or button callback
                     prefixed with 'btn:' (e.g. 'btn:cat:gold').
        """
        async with get_db_connection() as db:
            await db.execute(
                "INSERT INTO interactions (user_id, command) VALUES (?, ?)",
                (user_id, command)
            )
            await db.commit()

    @staticmethod
    async def get_most_used_command() -> dict | None:
        """Return the command with the highest usage count.

        Returns:
            Dict with keys 'command' and 'count', or None if no interactions exist.
        """
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT command, COUNT(*) as count
                FROM interactions
                GROUP BY command
                ORDER BY count DESC
                LIMIT 1
            """)
            row = await cursor.fetchone()
            return dict(row) if row else None


class ErrorRepository:
    """Data-access methods for the fetch_errors table."""

    @staticmethod
    async def log_error(source: str, error_message: str, error_type: str):
        """Record a fetch failure in the error log.

        Args:
            source:        'tgju' or 'nerkh'.
            error_message: str(exception).
            error_type:    type(exception).__name__ (e.g. 'ClientConnectorError').
        """
        async with get_db_connection() as db:
            await db.execute("""
                INSERT INTO fetch_errors (source, error_message, error_type)
                VALUES (?, ?, ?)
            """, (source, error_message, error_type))
            await db.commit()

    @staticmethod
    async def get_recent_errors(limit: int = 50) -> list[dict]:
        """Return the most recent fetch errors, newest first.

        Args:
            limit: Maximum number of rows to return (default 50).
        """
        async with get_db_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM fetch_errors ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


class UserSourceLogRepository:
    """Data-access methods for the user_source_logs audit table."""

    @staticmethod
    async def log_source_change(user_id: int, old_source: str, new_source: str):
        """Record that a user switched their preferred data source.

        Called only when old_source != new_source (handlers.py ensures this).
        """
        async with get_db_connection() as db:
            await db.execute("""
                INSERT INTO user_source_logs (user_id, old_source, new_source)
                VALUES (?, ?, ?)
            """, (user_id, old_source, new_source))
            await db.commit()

    @staticmethod
    async def get_recent_logs(limit: int = 50) -> list[dict]:
        """Return recent source-switch events joined with user display info.

        Args:
            limit: Maximum number of rows to return (default 50).

        Returns:
            List of dicts including all user_source_logs columns plus
            first_name and username from the users table.
        """
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT l.*, u.first_name, u.username
                FROM user_source_logs l
                JOIN users u ON l.user_id = u.user_id
                ORDER BY l.changed_at DESC LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
