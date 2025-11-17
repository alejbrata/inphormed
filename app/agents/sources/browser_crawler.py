# app/agents/sources/browser_crawler.py
from __future__ import annotations
import asyncio
import logging
from typing import Optional

# Intentamos importar playwright
try:
    from playwright.async_api import async_playwright
    import html2text
except ImportError:
    async_playwright = None

logger = logging.getLogger(__name__)

class BrowserCrawler:
    """
    Agente Navegador Completo.
    Usa un navegador Chromium real (headless) para renderizar la página,
    ejecutar JS y extraer el texto tal cual lo vería un humano.
    """

    def __init__(self):
        self.converter = html2text.HTML2Text()
        self.converter.ignore_links = True
        self.converter.ignore_images = True
        self.converter.ignore_emphasis = True

    async def fetch_full_text(self, url: str) -> Optional[str]:
        if async_playwright is None:
            print("BrowserCrawler: Falta 'playwright'. Ejecuta: pip install playwright && playwright install chromium")
            return None

        print(f"BrowserCrawler: Abriendo navegador para {url} ...")
        
        try:
            async with async_playwright() as p:
                # Lanzamos un navegador real (Chromium)
                browser = await p.chromium.launch(headless=True)
                
                # Creamos un contexto con un User-Agent muy común para no parecer robot
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # Navegamos
                try:
                    # Esperamos hasta que la red esté casi parada (significa que cargó todo)
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Pequeña espera extra para JS perezoso (NEJM/Oxford a veces tardan)
                    await page.wait_for_timeout(2000) 

                    # Truco: A veces hay modales de "Cookies". Intentamos cerrarlos o ignorarlos
                    # Extrayendo el texto del 'body'
                    content_html = await page.content()
                    
                    # Convertimos a texto limpio Markdown
                    text = self.converter.handle(content_html)
                    
                    # Limpieza post-proceso
                    if len(text) < 1000:
                         # Si es muy corto, quizá falló la carga.
                         print(f"BrowserCrawler: Texto muy corto ({len(text)} chars).")
                    else:
                         print(f"BrowserCrawler: ¡Éxito! Leídos {len(text)} caracteres.")

                    return text

                except Exception as e:
                    print(f"BrowserCrawler Navegación Error: {e}")
                    return None
                finally:
                    await browser.close()

        except Exception as e:
            print(f"BrowserCrawler Error General: {e}")
            return None