import asyncio
import logging
from src.services import tgju_fetcher
from src.services import nerkh_fetcher
from src.database.repositories import PriceRepository, ErrorRepository

logger = logging.getLogger(__name__)

async def fetch_and_store():
    logger.info("Starting price fetch cycle...")
    
    tgju_task = asyncio.create_task(tgju_fetcher.fetch())
    nerkh_task = asyncio.create_task(nerkh_fetcher.fetch())
    
    results = await asyncio.gather(tgju_task, nerkh_task, return_exceptions=True)
    
    tgju_result = results[0]
    nerkh_result = results[1]
    
    tgju_failed = False
    
    if isinstance(tgju_result, Exception):
        logger.error(f"TGJU fetch failed: {tgju_result}")
        await ErrorRepository.log_error("tgju", str(tgju_result), type(tgju_result).__name__)
        tgju_failed = True
    else:
        logger.info(f"Successfully fetched {len(tgju_result)} prices from TGJU.")
        await PriceRepository.upsert_many(tgju_result)
        
    if isinstance(nerkh_result, Exception):
        logger.error(f"Nerkh.io fetch failed: {nerkh_result}")
        await ErrorRepository.log_error("nerkh", str(nerkh_result), type(nerkh_result).__name__)
    else:
        if nerkh_result:
            logger.info(f"Successfully fetched {len(nerkh_result)} prices from Nerkh.")
            await PriceRepository.upsert_many(nerkh_result)

    logger.info("Price fetch cycle complete.")
