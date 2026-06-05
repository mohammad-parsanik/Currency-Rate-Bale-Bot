# Contributing to Currency Rate Bale Bot

This guide covers how to set up the dev environment, coding conventions, and how to extend the bot.

---

## Development Setup

```bash
git clone <your-repo-url>
cd "Currency Rate Bale Bot"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in BOT_TOKEN (NERKH_API_TOKEN is optional for local dev)
```

---

## Running Tests

The full test suite runs without any network access or real credentials:

```bash
pytest -v
```

Run with coverage to check untested paths:

```bash
pytest --cov=src --cov-report=term-missing
```

All new features must include tests. Keep the `conftest.py` fixtures shared; add feature-specific fixtures at the top of each test file.

---

## Code Conventions

- **Python 3.12+** — use modern type hints (`list[dict]`, `str | None`).
- **Async everywhere** — all I/O functions must be `async`. Never use blocking calls (`requests`, `open`, `time.sleep`) in async contexts.
- **Docstrings** — add a one-line docstring to every public function that isn't self-evident.
- **Module-level logger** — every module should declare `logger = logging.getLogger(__name__)`.
- **No hard-coded secrets** — all configurable values go in `src/config.py` via `Settings`.
- **Repository pattern** — all database access goes through the repository classes in `src/database/repositories.py`. Do not write raw SQL in handlers or services.

---

## Adding a New Tracked Asset

### Step 1 — Add to the TGJU asset map (`src/services/tgju_fetcher.py`)

```python
TGJU_ASSET_MAP = {
    # ... existing entries ...
    "tgju_new_key": {"code": "my_asset", "name": "نام فارسی", "category": "currency"},
}
```

`category` must be one of: `"currency"`, `"gold"`, `"coin"`.

### Step 2 — Add to the Nerkh asset map (`src/services/nerkh_fetcher.py`)

```python
NERKH_ASSET_MAP = {
    # ... existing entries ...
    "NERKH_SYMBOL": {"code": "my_asset", "name": "نام فارسی", "category": "currency"},
}
```

Use the same `code` value as in the TGJU map so both sources share the same primary key in the database.

### Step 3 — No other changes needed

The database schema stores all assets generically. The formatter groups them by `category` automatically.

---

## Adding a New Data Source

1. Create `src/services/<source>_fetcher.py` with an `async def fetch() -> list[dict]` function.  
   Each item in the returned list must have the keys: `asset_code`, `asset_name_fa`, `category`, `price`, `price_high`, `price_low`, `change_amount`, `change_percent`, `change_direction`, `source`, `source_timestamp`.
2. Import and call your fetcher in `src/services/price_service.py` alongside the existing ones.
3. Add `source` to the `preferred_source` options in `src/bot/keyboards.py` (`get_settings_keyboard`).
4. Add fixture data and tests in `tests/test_<source>_fetcher.py`.

---

## Pull Request Checklist

- [ ] Tests pass locally (`pytest -v`).
- [ ] New code is covered by tests.
- [ ] No secrets or real credentials committed.
- [ ] Docstrings added for new public functions.
- [ ] `README.md` updated if user-facing behavior changed (new asset, new command, etc.).
