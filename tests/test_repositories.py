"""
Tests for src/database/repositories.py

Every test uses the ``db`` fixture from conftest which:
  • Creates a temporary SQLite file in ``tmp_path``
  • Patches ``src.config.settings.DB_PATH`` and
    ``src.database.connection.settings.DB_PATH`` to point there
  • Runs ``init_db()`` so all tables exist
"""

import pytest

from src.database.repositories import (
    PriceRepository,
    UserRepository,
    InteractionRepository,
    ErrorRepository,
    UserSourceLogRepository,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_price(
    asset_code: str = "usd",
    asset_name_fa: str = "دلار آمریکا",
    category: str = "currency",
    price: str = "85000",
    source: str = "tgju",
    source_timestamp: str | None = "2026-06-05 12:00:00",
    **overrides,
) -> dict:
    """Return a minimal price dict accepted by ``PriceRepository.upsert_many``."""
    base = {
        "asset_code": asset_code,
        "asset_name_fa": asset_name_fa,
        "category": category,
        "price": price,
        "price_high": "85500",
        "price_low": "84500",
        "change_amount": "500",
        "change_percent": 0.59,
        "change_direction": "high",
        "source": source,
        "source_timestamp": source_timestamp,
    }
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════════════════
# PriceRepository
# ═══════════════════════════════════════════════════════════════════════════

class TestPriceRepository:
    """Tests for ``PriceRepository``."""

    @pytest.mark.asyncio
    async def test_upsert_many_prices(self, db):
        """Inserting 3 distinct prices → get_all_prices returns all 3."""
        prices = [
            _make_price(asset_code="usd"),
            _make_price(asset_code="eur", asset_name_fa="یورو", price="92000"),
            _make_price(asset_code="gbp", asset_name_fa="پوند", price="108000"),
        ]
        await PriceRepository.upsert_many(prices)

        rows = await PriceRepository.get_all_prices("tgju")
        assert len(rows) == 3
        codes = {r["asset_code"] for r in rows}
        assert codes == {"usd", "eur", "gbp"}

    @pytest.mark.asyncio
    async def test_upsert_many_updates_existing(self, db):
        """Upserting the same (asset_code, source) updates the price."""
        await PriceRepository.upsert_many([_make_price(price="85000")])
        # same asset_code + source, different price
        await PriceRepository.upsert_many([_make_price(price="90000")])

        row = await PriceRepository.get_price("usd", "tgju")
        assert row is not None
        assert row["price"] == "90000"

    @pytest.mark.asyncio
    async def test_upsert_many_empty_list(self, db):
        """Passing an empty list causes no error and no rows."""
        await PriceRepository.upsert_many([])  # should not raise
        rows = await PriceRepository.get_all_prices("tgju")
        assert rows == []

    @pytest.mark.asyncio
    async def test_get_all_prices_by_source(self, db):
        """Filtering by source returns only the matching rows."""
        await PriceRepository.upsert_many([
            _make_price(asset_code="usd", source="tgju"),
            _make_price(asset_code="eur", source="tgju"),
            _make_price(asset_code="usd", source="nerkh"),
        ])

        tgju = await PriceRepository.get_all_prices("tgju")
        nerkh = await PriceRepository.get_all_prices("nerkh")

        assert len(tgju) == 2
        assert len(nerkh) == 1
        assert nerkh[0]["asset_code"] == "usd"
        assert nerkh[0]["source"] == "nerkh"

    @pytest.mark.asyncio
    async def test_get_price_single(self, db):
        """get_price returns the exact matching row as a dict."""
        await PriceRepository.upsert_many([
            _make_price(asset_code="usd", source="tgju", price="85000"),
        ])

        row = await PriceRepository.get_price("usd", "tgju")
        assert row is not None
        assert row["asset_code"] == "usd"
        assert row["source"] == "tgju"
        assert row["price"] == "85000"
        assert row["asset_name_fa"] == "دلار آمریکا"

    @pytest.mark.asyncio
    async def test_get_price_not_found(self, db):
        """get_price returns None for a non-existent asset."""
        result = await PriceRepository.get_price("xxx", "tgju")
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_price_missing_optional(self, db):
        """source_timestamp=None does not crash the upsert."""
        price = _make_price(source_timestamp=None)
        await PriceRepository.upsert_many([price])  # should not raise

        row = await PriceRepository.get_price("usd", "tgju")
        assert row is not None
        assert row["source_timestamp"] is None


# ═══════════════════════════════════════════════════════════════════════════
# UserRepository
# ═══════════════════════════════════════════════════════════════════════════

class TestUserRepository:
    """Tests for ``UserRepository``."""

    @pytest.mark.asyncio
    async def test_upsert_user(self, db):
        """New user gets default preferred_source='tgju'."""
        await UserRepository.upsert_user(1001, "علی", "محمدی", "ali_m")

        user = await UserRepository.get_user(1001)
        assert user is not None
        assert user["first_name"] == "علی"
        assert user["last_name"] == "محمدی"
        assert user["username"] == "ali_m"
        assert user["preferred_source"] == "tgju"

    @pytest.mark.asyncio
    async def test_upsert_user_updates_existing(self, db):
        """Re-upserting updates names but preserves preferred_source."""
        await UserRepository.upsert_user(1001, "علی", "محمدی", "ali_m")
        # Change preferred source first
        await UserRepository.update_preferred_source(1001, "nerkh")

        # Now upsert again with a new name
        await UserRepository.upsert_user(1001, "حسین", "رضایی", "hossein_r")

        user = await UserRepository.get_user(1001)
        assert user["first_name"] == "حسین"
        assert user["last_name"] == "رضایی"
        assert user["username"] == "hossein_r"
        # preferred_source must NOT have been overwritten
        assert user["preferred_source"] == "nerkh"

    @pytest.mark.asyncio
    async def test_get_user_found(self, db):
        """get_user returns a dict when the user exists."""
        await UserRepository.upsert_user(42, "Sara", "K", "sara_k")

        user = await UserRepository.get_user(42)
        assert isinstance(user, dict)
        assert user["user_id"] == 42

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, db):
        """get_user returns None for a non-existent user_id."""
        assert await UserRepository.get_user(999999) is None

    @pytest.mark.asyncio
    async def test_update_preferred_source(self, db):
        """update_preferred_source changes the stored source."""
        await UserRepository.upsert_user(1001, "علی", "محمدی", "ali_m")
        assert (await UserRepository.get_user(1001))["preferred_source"] == "tgju"

        await UserRepository.update_preferred_source(1001, "nerkh")
        assert (await UserRepository.get_user(1001))["preferred_source"] == "nerkh"

    @pytest.mark.asyncio
    async def test_get_stats(self, db):
        """get_stats returns total, active count, and recent_users list."""
        await UserRepository.upsert_user(1, "A", "A", "a")
        await UserRepository.upsert_user(2, "B", "B", "b")
        await UserRepository.upsert_user(3, "C", "C", "c")

        stats = await UserRepository.get_stats()

        assert stats["total"] == 3
        # All three were just inserted → last_seen_at is now → all active
        assert stats["active"] == 3
        assert len(stats["recent_users"]) == 3
        # recent_users should be dicts
        assert isinstance(stats["recent_users"][0], dict)


# ═══════════════════════════════════════════════════════════════════════════
# InteractionRepository
# ═══════════════════════════════════════════════════════════════════════════

class TestInteractionRepository:
    """Tests for ``InteractionRepository``."""

    @pytest.mark.asyncio
    async def test_log_interaction(self, db):
        """log_interaction inserts without error."""
        # Need a user for FK (SQLite doesn't enforce FKs by default, but
        # let's keep the data consistent)
        await UserRepository.upsert_user(1, "A", "A", "a")
        await InteractionRepository.log_interaction(1, "/start")
        # No exception means success

    @pytest.mark.asyncio
    async def test_get_most_used_command(self, db):
        """The command logged most frequently is returned with its count."""
        await UserRepository.upsert_user(1, "A", "A", "a")

        await InteractionRepository.log_interaction(1, "/start")
        await InteractionRepository.log_interaction(1, "/start")
        await InteractionRepository.log_interaction(1, "/start")
        await InteractionRepository.log_interaction(1, "/price")

        result = await InteractionRepository.get_most_used_command()
        assert result is not None
        assert result["command"] == "/start"
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_get_most_used_command_empty(self, db):
        """Returns None when no interactions have been logged."""
        result = await InteractionRepository.get_most_used_command()
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# ErrorRepository
# ═══════════════════════════════════════════════════════════════════════════

class TestErrorRepository:
    """Tests for ``ErrorRepository``."""

    @pytest.mark.asyncio
    async def test_log_error(self, db):
        """log_error inserts without error."""
        await ErrorRepository.log_error("tgju", "Connection timeout", "TimeoutError")
        # No exception means success

    @pytest.mark.asyncio
    async def test_get_recent_errors(self, db):
        """Errors are returned in descending order by created_at."""
        await ErrorRepository.log_error("tgju", "err1", "Type1")
        await ErrorRepository.log_error("nerkh", "err2", "Type2")
        await ErrorRepository.log_error("tgju", "err3", "Type3")

        errors = await ErrorRepository.get_recent_errors()
        assert len(errors) == 3
        # DESC order → most recent first
        assert errors[0]["error_message"] == "err3"
        assert errors[1]["error_message"] == "err2"
        assert errors[2]["error_message"] == "err1"

    @pytest.mark.asyncio
    async def test_get_recent_errors_limit(self, db):
        """The limit parameter caps the number of returned rows."""
        for i in range(5):
            await ErrorRepository.log_error("src", f"err{i}", "T")

        errors = await ErrorRepository.get_recent_errors(limit=2)
        assert len(errors) == 2


# ═══════════════════════════════════════════════════════════════════════════
# UserSourceLogRepository
# ═══════════════════════════════════════════════════════════════════════════

class TestUserSourceLogRepository:
    """Tests for ``UserSourceLogRepository``."""

    @pytest.mark.asyncio
    async def test_log_source_change(self, db):
        """log_source_change inserts without error."""
        await UserRepository.upsert_user(1, "A", "A", "a")
        await UserSourceLogRepository.log_source_change(1, "tgju", "nerkh")
        # No exception means success

    @pytest.mark.asyncio
    async def test_get_recent_source_logs(self, db):
        """get_recent_logs JOINs with users and returns enriched rows."""
        await UserRepository.upsert_user(1, "Ali", "M", "ali_m")
        await UserSourceLogRepository.log_source_change(1, "tgju", "nerkh")
        await UserSourceLogRepository.log_source_change(1, "nerkh", "tgju")

        logs = await UserSourceLogRepository.get_recent_logs()
        assert len(logs) == 2

        # Most recent first (DESC)
        assert logs[0]["new_source"] == "tgju"
        assert logs[0]["old_source"] == "nerkh"
        assert logs[1]["new_source"] == "nerkh"
        assert logs[1]["old_source"] == "tgju"

        # JOIN columns present
        assert logs[0]["first_name"] == "Ali"
        assert logs[0]["username"] == "ali_m"
