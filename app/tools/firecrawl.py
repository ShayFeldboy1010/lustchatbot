import httpx
import logging
from typing import Optional
from ..settings import settings

logger = logging.getLogger(__name__)


async def firecrawl_scrape(url: str) -> str:
    """
    Scrape website content using Firecrawl API
    
    Args:
        url: URL to scrape
        
    Returns:
        Scraped content as string
    """
    try:
        headers = {
            "Authorization": f"Bearer {settings.firecrawl_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "formats": ["markdown"],
            "only_main_content": True,
            "timeout": 30
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("data", {}).get("markdown", "")
                logger.info(f"Successfully scraped {url}")
                return content
            else:
                logger.error(f"Firecrawl API error {response.status_code}: {response.text}")
                return f"Error scraping {url}: {response.status_code}"
                
    except Exception as e:
        logger.error(f"Firecrawl scrape failed for {url}: {e}")
        return f"Failed to scrape {url}: {str(e)}"


def firecrawl_scrape_sync(url: str) -> str:
    """
    Synchronous version of firecrawl_scrape for LangChain tools
    """
    import asyncio
    
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, we need to create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, firecrawl_scrape(url))
                return future.result()
        else:
            # We can run the coroutine directly
            return asyncio.run(firecrawl_scrape(url))
    except Exception as e:
        logger.error(f"Sync firecrawl failed: {e}")
        return f"Failed to scrape {url}: {str(e)}"


# For LangChain tool compatibility
firecrawl_scrape = firecrawl_scrape_sync
