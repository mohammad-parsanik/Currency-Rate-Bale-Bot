import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import settings
import aiohttp

async def test_nerkh_raw():
    headers = {"Authorization": f"Bearer {settings.NERKH_API_TOKEN}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(settings.NERKH_URL, headers=headers) as response:
            data = await response.json()
            # print top level keys
            print(f"Keys: {data.keys()}")
            print(data)

asyncio.run(test_nerkh_raw())
