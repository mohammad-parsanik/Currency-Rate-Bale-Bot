# Currency Rate Bale Bot 🤖

A production-grade Telegram/Bale bot that fetches currency and gold rates from two distinct sources (`tgju.org` and `nerkh.io`), caches them locally in SQLite, and provides an admin panel dashboard.

## Features
- **Concurrent Fetching:** Uses `asyncio` and `aiohttp` to fetch from multiple APIs every 5 minutes.
- **Bale Platform Support:** Uses raw API requests targeting `tapi.bale.ai`.
- **Farsi Localization:** Numbers are formatted to Persian numerals with Toman as the primary currency unit.
- **Admin Dashboard:** FastAPI dashboard protected by basic authentication to view stats and logs.
- **Dockerized:** Ready for deployment with `docker-compose`.

## Prerequisites
- Python 3.12+ (if running locally)
- Docker and Docker Compose (if running via Docker)
- A Bot Token from BotFather in Bale Messenger.
- An API Token from [Nerkh.io](https://nerkh.io).

## Getting Started

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <your-repo-url>
   cd "Currency Rate Bale Bot"
   ```

2. Rename `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   *Make sure you provide valid values for `BOT_TOKEN` and `NERKH_API_TOKEN`.*

### Run Locally (Without Docker)

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   pip install -r requirements.txt
   ```
2. Start the bot:
   ```bash
   python main.py
   ```

### Run with Docker (Recommended for Production)

Docker provides an isolated environment for the bot and admin panel.

1. Build and start the container in detached mode:
   ```bash
   docker-compose up -d --build
   ```
2. To view the bot's logs:
   ```bash
   docker-compose logs -f bot
   ```
3. To stop the container:
   ```bash
   docker-compose down
   ```

### Admin Panel
Once the application is running, navigate to `http://localhost:8080` in your web browser to access the admin panel. 
Default credentials are `admin` / `admin` unless changed in the `.env` file.
