import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services import nerkh_fetcher
from src.config import settings

async def test_nerkh():
    print("Fetching from Nerkh...")
    if not settings.NERKH_API_TOKEN:
        print("Warning: NERKH_API_TOKEN is not set in config.")
    try:
        results = await nerkh_fetcher.fetch()
        print(f"Successfully fetched {len(results)} items from Nerkh.")
        for item in results:
            print(f"- {item['asset_name_fa']} ({item['asset_code']}): {item['price']} (High: {item['price_high']}, Low: {item['price_low']})")
    except Exception as e:
        print(f"Error fetching from Nerkh: {e}")

if __name__ == "__main__":
    asyncio.run(test_nerkh())
