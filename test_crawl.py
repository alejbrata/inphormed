import asyncio
from app.agents.sources.browser_crawler import BrowserCrawler

async def test():
    bc = BrowserCrawler()
    url = "https://example.com"
    print(f"Fetching {url}...")
    text = await bc.fetch_full_text(url)
    print(f"Result length: {len(text) if text else 'None'}")
    if text:
        print(f"Preview: {text[:100]}")

if __name__ == "__main__":
    asyncio.run(test())
