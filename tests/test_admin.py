"""
Tests for the admin panel FastAPI application (src/admin/app.py).

Covers:
  - HTTP Basic authentication (success / wrong password / no header)
  - Dashboard rendering with empty DB, seeded DB data, and edge cases
  - Manual scrape endpoint (success, auth failure, fetch exception)
  - XSS protection in rendered HTML
  - latest_update "N/A" fallback when no prices exist
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock

from src.admin.app import app
from src.database.repositories import (
    PriceRepository,
    UserRepository,
    InteractionRepository,
    ErrorRepository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client(**kwargs) -> httpx.AsyncClient:
    """Return an httpx.AsyncClient wired to the FastAPI app under test."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test", **kwargs)


VALID_AUTH = ("admin", "admin")
WRONG_AUTH = ("admin", "wrongpassword")


# ===========================================================================
# Authentication tests
# ===========================================================================


class TestDashboardAuth:
    """Verify HTTP-Basic authentication on the dashboard endpoint."""

    @pytest.mark.asyncio
    async def test_dashboard_auth_success(self, db):
        """GET / with valid credentials returns 200."""
        async with _client() as ac:
            resp = await ac.get("/", auth=VALID_AUTH)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_auth_failure(self, db):
        """GET / with wrong password returns 401."""
        async with _client() as ac:
            resp = await ac.get("/", auth=WRONG_AUTH)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_dashboard_no_auth(self, db):
        """GET / without an Authorization header returns 401."""
        async with _client() as ac:
            resp = await ac.get("/")
        assert resp.status_code == 401


# ===========================================================================
# Dashboard rendering tests
# ===========================================================================


class TestDashboardRendering:
    """Dashboard HTML rendering with various DB states."""

    @pytest.mark.asyncio
    async def test_dashboard_empty_db(self, db):
        """With an empty database the dashboard still returns 200 (no 500)."""
        async with _client() as ac:
            resp = await ac.get("/", auth=VALID_AUTH)
        assert resp.status_code == 200
        body = resp.text
        # Zero users
        assert "0" in body

    @pytest.mark.asyncio
    async def test_dashboard_with_data(self, db):
        """Seed users, prices, and errors — verify the dashboard reflects them."""
        # --- Seed users ---
        await UserRepository.upsert_user(1001, "Alice", "Smith", "alice_s")
        await UserRepository.upsert_user(1002, "Bob", "Jones", "bob_j")

        # --- Seed prices (tgju) ---
        await PriceRepository.upsert_many([
            {
                "asset_code": "usd",
                "asset_name_fa": "دلار آمریکا",
                "category": "currency",
                "price": "850000",
                "price_high": "855000",
                "price_low": "845000",
                "change_amount": "5000",
                "change_percent": 0.59,
                "change_direction": "high",
                "source": "tgju",
                "source_timestamp": "2026-06-05 12:00:00",
            }
        ])

        # --- Seed an error ---
        await ErrorRepository.log_error("tgju", "Timeout connecting", "TimeoutError")

        # --- Seed an interaction ---
        await InteractionRepository.log_interaction(1001, "/start")

        async with _client() as ac:
            resp = await ac.get("/", auth=VALID_AUTH)

        assert resp.status_code == 200
        body = resp.text
        # Total users count should be 2
        assert "2" in body
        # The error info should appear
        assert "Timeout connecting" in body
        # User name should appear
        assert "Alice" in body

    @pytest.mark.asyncio
    async def test_dashboard_most_used_none(self, db):
        """When there are no interactions, the most-used command shows 'None'."""
        async with _client() as ac:
            resp = await ac.get("/", auth=VALID_AUTH)
        assert resp.status_code == 200
        assert "None" in resp.text

    @pytest.mark.asyncio
    async def test_dashboard_latest_update_no_prices(self, db):
        """When no prices exist, latest_update should be 'N/A'."""
        async with _client() as ac:
            resp = await ac.get("/", auth=VALID_AUTH)
        assert resp.status_code == 200
        assert "N/A" in resp.text

    @pytest.mark.asyncio
    async def test_dashboard_xss_in_username(self, db):
        """A user with a <script> tag in first_name is HTML-escaped in output."""
        xss_payload = "<script>alert('xss')</script>"
        await UserRepository.upsert_user(9999, xss_payload, "", "hacker")

        async with _client() as ac:
            resp = await ac.get("/", auth=VALID_AUTH)

        assert resp.status_code == 200
        body = resp.text
        # The raw script tag must NOT appear in the response
        assert xss_payload not in body
        # The escaped form should be present instead
        assert "&lt;script&gt;" in body


# ===========================================================================
# Manual scrape endpoint tests
# ===========================================================================


class TestManualScrape:
    """POST /api/scrape endpoint tests."""

    @pytest.mark.asyncio
    async def test_manual_scrape_auth_success(self, db):
        """POST /api/scrape with valid creds and successful fetch returns 200."""
        with patch("src.admin.app.fetch_and_store", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            async with _client() as ac:
                resp = await ac.post("/api/scrape", auth=VALID_AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "Scrape completed" in data["message"]
        mock_fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_manual_scrape_auth_failure(self, db):
        """POST /api/scrape with wrong creds returns 401."""
        async with _client() as ac:
            resp = await ac.post("/api/scrape", auth=WRONG_AUTH)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_manual_scrape_fetch_fails(self, db):
        """POST /api/scrape returns 500 when fetch_and_store raises."""
        with patch(
            "src.admin.app.fetch_and_store",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Network failure"),
        ):
            async with _client() as ac:
                resp = await ac.post("/api/scrape", auth=VALID_AUTH)

        assert resp.status_code == 500
        assert "Network failure" in resp.json()["detail"]
