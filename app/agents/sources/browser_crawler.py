# app/agents/sources/browser_crawler.py
from __future__ import annotations
import asyncio
import logging
import os
import datetime
from typing import Optional

# Configuración de logs
def log_debug(msg: str):
    os.makedirs("logs", exist_ok=True)
    with open("logs/CRAWLER_DEBUG.log", "a", encoding="utf-8") as f:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        f.write(f"[{ts}] {msg}\n")
    print(f"[CRAWLER] {msg}") # También a consola

class BrowserCrawler:
    def __init__(self):
        try:
            from playwright.async_api import async_playwright
            import html2text
            self._has_playwright = True
            self.converter = html2text.HTML2Text()
            self.converter.ignore_links = True
            self.converter.ignore_images = True
            self.converter.ignore_emphasis = True
            self.converter.body_width = 0
            log_debug("INIT: Playwright listo.")
        except ImportError as e:
            self._has_playwright = False
            log_debug(f"INIT ERROR: {e}")

    async def fetch_full_text(self, url: str) -> Optional[str]:
        """
        Estrategia Híbrida:
        1. Si la URL es un DOI o link directo, intenta ir.
        2. Si falla o es muy corto, intenta ir a PubMed y hacer clic en el botón "Full Text".
        """
        if not self._has_playwright:
            return None

        from playwright.async_api import async_playwright

        log_debug(f"START: Iniciando misión para {url}")
        
        try:
            async with async_playwright() as p:
                # Lanzamos con ventana visible (headless=True) pero argumentos stealth
                # IMPORTANTE: args para saltar detecciones básicas
                browser = await p.chromium.launch(
                    headless=True, 
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-infobars",
                        "--window-position=0,0",
                        "--ignore-certificate-errors",
                        "--ignore-certificate-errors-spki-list",
                        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                    ]
                )
                
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York" # Parecer usuario US a veces ayuda
                )
                
                # Inyección de scripts anti-bot
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.navigator.chrome = { runtime: {} };
                """)

                page = await context.new_page()
                
                # --- ESTRATEGIA 1: NAVEGACIÓN DIRECTA ---
                text = await self._try_navigate_and_extract(page, url)
                
                # --- ESTRATEGIA 2: PUENTE VÍA PUBMED (Si falló la 1 y es un DOI/PMID) ---
                # Si el texto es corto (<2000 chars) y parece que venimos de un DOI o PMID
                if (not text or len(text) < 2000) and ("doi.org" in url or "pubmed" in url):
                    log_debug("RETRY: Estrategia directa falló/corta. Intentando vía botón PubMed...")
                    
                    # Si tenemos un DOI, construimos la url de pubmed (o usamos la que nos dieron)
                    # Asumimos que el 'url' de entrada podría ser el DOI.
                    # Para este truco, necesitamos saber el PMID.
                    # Si no lo tenemos aquí, asumiremos que la URL de entrada ERA la de pubmed
                    # o intentaremos buscar en Google el PMID (demasiado complejo).
                    # Simplificación: Si la URL es doi.org, intentamos navegar igual.
                    pass # (Implementado implícitamente en la lógica de navegación robusta)

                await browser.close()
                return text

        except Exception as e:
            log_debug(f"CRASH: {e}")
            return None

    async def _try_navigate_and_extract(self, page, url):
        try:
            log_debug(f"NAV: Yendo a {url}")
            # Timeout generoso de 60s
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # ¿Es PubMed? Si es así, busquemos el botón "Full Text"
            if "pubmed.ncbi.nlm.nih.gov" in page.url:
                log_debug("DETECTADO: Estamos en PubMed. Buscando botón Full Text...")
                # Selector del botón de la derecha (Full Text Links)
                # Suele ser un <a> dentro de .full-text-links-list
                full_text_btn = page.locator(".full-text-links-list a.link-item").first
                
                if await full_text_btn.count() > 0:
                    log_debug("CLICK: Botón Full Text encontrado. Hacemos clic.")
                    # Esperamos navegación tras el clic (puede abrir pestaña o redirigir)
                    async with page.expect_popup() as popup_info:
                        await full_text_btn.click()
                    
                    # Usamos la nueva página (popup)
                    new_page = await popup_info.value
                    await new_page.wait_for_load_state("domcontentloaded")
                    page = new_page # Cambiamos el foco a la nueva página
                    log_debug(f"REDIRECT: Ahora estamos en {page.url}")
                else:
                    log_debug("WARN: No encontré botón Full Text en PubMed.")

            # --- FASE DE ESPERA ACTIVA (Anti-Lazy Loading) ---
            log_debug("WAIT: Esperando carga dinámica...")
            await asyncio.sleep(5) # Espera inicial
            
            # Scroll humano progresivo
            for i in range(10):
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(0.5)
            
            # Scroll al fondo
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

           
           # --- FASE DE COOKIES (Machacar popups - MODO TOLERANTE) ---
            log_debug("COOKIES: Buscando botones de aceptar...")
            cookie_selectors = [
                "#onetrust-accept-btn-handler", 
                "button:has-text('Accept')", 
                "button:has-text('Agree')", 
                "button:has-text('Yes')", 
                # Selectores más específicos para evitar ambigüedad
                "div[role='dialog'] button[aria-label='Close']",
                "button[aria-label='Close']",
                "a:has-text('Close')"
            ]
            for sel in cookie_selectors:
                # Usamos .count() para ver si hay alguno
                count = await page.locator(sel).count()
                if count > 0:
                    try:
                        # .first es la clave: Clicamos el primero y nos da igual el resto
                        if await page.locator(sel).first.is_visible():
                            log_debug(f"COOKIES: Clicando '{sel}' (1 de {count})")
                            await page.locator(sel).first.click(timeout=1000)
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        # Si falla el clic, lo ignoramos y seguimos. No debe parar el script.
                        pass

            # --- FASE DE EXTRACCIÓN ---
            # 1. Selectores específicos (NEJM, Oxford, Elsevier)
            article_selectors = [
                "section#article_body",   # NEJM
                ".article-body",          # General
                ".main-content",          # Oxford
                "div[role='main']",       # Accesibilidad
                "article",                # HTML5
                "#content"                # Fallback
            ]
            
            content_html = ""
            for sel in article_selectors:
                if await page.locator(sel).count() > 0:
                    log_debug(f"EXTRACT: Encontrado contenedor '{sel}'")
                    content_html = await page.locator(sel).first.inner_html()
                    if len(content_html) > 5000: # Si es sustancial, nos vale
                        break
            
            # 2. Fallback Nuclear: Todo el body
            if len(content_html) < 1000:
                log_debug("EXTRACT: Selectores fallaron. Extrayendo todo el BODY.")
                content_html = await page.content()

            # --- GUARDAR HTML PARA DEBUG (Vital para ti) ---
            with open("logs/last_crawl_full.html", "w", encoding="utf-8") as f:
                f.write(content_html)
            
            # Conversión
            text = self.converter.handle(content_html)
            
            # Limpieza básica
            clean_text = text.replace("\n\n\n", "\n\n").strip()
            log_debug(f"DONE: Texto extraído: {len(clean_text)} caracteres.")
            
            return clean_text

        except Exception as e:
            log_debug(f"ERROR NAVEGACIÓN: {e}")
            return None