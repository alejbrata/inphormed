# app/agents/sources/browser_crawler.py
from __future__ import annotations
import asyncio
import os
import datetime
from typing import Optional

# Logger manual a fichero para asegurar que vemos qué pasa
def log_debug(msg: str):
    os.makedirs("logs", exist_ok=True)
    with open("logs/CRAWLER_DEBUG.log", "a", encoding="utf-8") as f:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        f.write(f"[{ts}] {msg}\n")

class BrowserCrawler:
    def __init__(self):
        # Intentamos importar aquí y logueamos el resultado
        try:
            from playwright.async_api import async_playwright
            import html2text
            self._has_playwright = True
            self.converter = html2text.HTML2Text()
            self.converter.ignore_links = True
            self.converter.ignore_images = True
            self.converter.body_width = 0
            log_debug("INIT: Playwright y html2text importados correctamente.")
        except ImportError as e:
            self._has_playwright = False
            log_debug(f"INIT ERROR: Falta librería. {e}")
        except Exception as e:
            self._has_playwright = False
            log_debug(f"INIT ERROR CRÍTICO: {e}")

    async def fetch_full_text(self, url: str) -> Optional[str]:
        log_debug(f"START: Petición para URL: {url}")

        if not self._has_playwright:
            log_debug("ABORT: No hay playwright instalado.")
            return None

        from playwright.async_api import async_playwright

        try:
            log_debug("LAUNCH: Iniciando navegador Chromium...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True, 
                    args=["--disable-blink-features=AutomationControlled"]
                )
                log_debug("LAUNCH: Navegador abierto.")
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    extra_http_headers={"Referer": "https://pubmed.ncbi.nlm.nih.gov/"}
                )
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                page = await context.new_page()
                log_debug(f"GOTO: Navegando a {url} (Timeout 60s)...")

                try:
                    # Navegación
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    status = response.status if response else "Unknown"
                    log_debug(f"GOTO DONE: Status {status}. URL final: {page.url}")

                    # Scroll
                    log_debug("SCROLL: Iniciando scroll...")
                    for i in range(4):
                        await page.evaluate("window.scrollBy(0, 800)")
                        await asyncio.sleep(0.5)
                    
                    # Cookies
                    try:
                        if await page.locator("button:has-text('Accept')").count() > 0:
                            log_debug("COOKIES: Botón detectado, click.")
                            await page.click("button:has-text('Accept')", timeout=1000)
                    except:
                        pass

                    # Extracción
                    content_html = await page.content()
                    
                    # Guardar HTML para inspección visual
                    with open("logs/last_crawl_dump.html", "w", encoding="utf-8") as f:
                        f.write(content_html)
                    log_debug("DUMP: HTML guardado en logs/last_crawl_dump.html")

                    text = self.converter.handle(content_html)
                    
                    # Limpieza
                    text = text.replace("\n\n\n", "\n\n").strip()
                    log_debug(f"EXTRACT: Texto extraído. Longitud: {len(text)} chars.")

                    if len(text) < 500:
                        log_debug("WARNING: Texto muy corto. Posible bloqueo.")
                    
                    return text

                except Exception as e:
                    log_debug(f"ERROR NAVEGACIÓN: {type(e).__name__}: {e}")
                    return None
                finally:
                    await browser.close()
                    log_debug("CLOSE: Navegador cerrado.")

        except Exception as e:
            log_debug(f"ERROR GENERAL: {type(e).__name__}: {e}")
            return None