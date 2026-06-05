import logging
from src.database.connection import get_db_connection

logger = logging.getLogger(__name__)

class PriceRepository:
    @staticmethod
    async def upsert_many(prices: list[dict]):
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
                        asset_name_fa=excluded.asset_name_fa,
                        category=excluded.category,
                        price=excluded.price,
                        price_high=excluded.price_high,
                        price_low=excluded.price_low,
                        change_amount=excluded.change_amount,
                        change_percent=excluded.change_percent,
                        change_direction=excluded.change_direction,
                        source_timestamp=excluded.source_timestamp,
                        fetched_at=CURRENT_TIMESTAMP
                """, (
                    p['asset_code'], p['asset_name_fa'], p['category'], p['price'], p['price_high'], p['price_low'],
                    p['change_amount'], p['change_percent'], p['change_direction'], p['source'], p.get('source_timestamp')
                ))
            await db.commit()

    @staticmethod
    async def get_all_prices(source: str):
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM prices WHERE source = ?", (source,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
    @staticmethod
    async def get_price(asset_code: str, source: str):
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM prices WHERE asset_code = ? AND source = ?", (asset_code, source))
            row = await cursor.fetchone()
            return dict(row) if row else None


class UserRepository:
    @staticmethod
    async def upsert_user(user_id: int, first_name: str, last_name: str, username: str):
        async with get_db_connection() as db:
            # We don't overwrite preferred_source if the user already exists
            await db.execute("""
                INSERT INTO users (user_id, first_name, last_name, username)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    username=excluded.username,
                    last_seen_at=CURRENT_TIMESTAMP
            """, (user_id, first_name, last_name, username))
            await db.commit()

    @staticmethod
    async def get_user(user_id: int):
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def update_preferred_source(user_id: int, new_source: str):
        async with get_db_connection() as db:
            await db.execute("UPDATE users SET preferred_source = ? WHERE user_id = ?", (new_source, user_id))
            await db.commit()

    @staticmethod
    async def get_stats():
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT COUNT(*) as total FROM users")
            total = (await cursor.fetchone())['total']
            
            cursor = await db.execute("SELECT COUNT(*) as active FROM users WHERE last_seen_at >= datetime('now', '-1 day')")
            active = (await cursor.fetchone())['active']
            
            cursor = await db.execute("SELECT * FROM users ORDER BY last_seen_at DESC LIMIT 50")
            recent_users = [dict(row) for row in await cursor.fetchall()]
            
            return {"total": total, "active": active, "recent_users": recent_users}


class InteractionRepository:
    @staticmethod
    async def log_interaction(user_id: int, command: str):
        async with get_db_connection() as db:
            await db.execute("INSERT INTO interactions (user_id, command) VALUES (?, ?)", (user_id, command))
            await db.commit()

    @staticmethod
    async def get_most_used_command():
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
    @staticmethod
    async def log_error(source: str, error_message: str, error_type: str):
        async with get_db_connection() as db:
            await db.execute("""
                INSERT INTO fetch_errors (source, error_message, error_type)
                VALUES (?, ?, ?)
            """, (source, error_message, error_type))
            await db.commit()
            
    @staticmethod
    async def get_recent_errors(limit: int = 50):
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM fetch_errors ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

class UserSourceLogRepository:
    @staticmethod
    async def log_source_change(user_id: int, old_source: str, new_source: str):
        async with get_db_connection() as db:
            await db.execute("""
                INSERT INTO user_source_logs (user_id, old_source, new_source)
                VALUES (?, ?, ?)
            """, (user_id, old_source, new_source))
            await db.commit()

    @staticmethod
    async def get_recent_logs(limit: int = 50):
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT l.*, u.first_name, u.username 
                FROM user_source_logs l
                JOIN users u ON l.user_id = u.user_id
                ORDER BY l.changed_at DESC LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
