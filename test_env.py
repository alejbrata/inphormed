import sys
try:
    import playwright
    print("Playwright: OK")
except ImportError as e:
    print(f"Playwright: FAIL {e}")

try:
    import html2text
    print("html2text: OK")
except ImportError as e:
    print(f"html2text: FAIL {e}")

try:
    from app.agents.sources.browser_crawler import BrowserCrawler
    bc = BrowserCrawler()
    print(f"Crawler Init: {bc._has_playwright}")
except Exception as e:
    print(f"Crawler Init: FAIL {e}")
