import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services import tgju_fetcher

async def test_tgju():
    print("Fetching from TGJU...")
    try:
        results = await tgju_fetcher.fetch()
        print(f"Successfully fetched {len(results)} items from TGJU.")
        for item in results:
            print(f"- {item['asset_name_fa']} ({item['asset_code']}): {item['price']} (High: {item['price_high']}, Low: {item['price_low']})")
    except Exception as e:
        print(f"Error fetching from TGJU: {e}")

if __name__ == "__main__":
    asyncio.run(test_tgju())
