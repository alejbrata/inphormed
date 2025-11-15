# app/agents/sources/pmc_crawler.py
from __future__ import annotations
import httpx
import re # <-- Corregido (movido al principio)
from typing import Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class PMCCrawler:
    """
    Agente-Herramienta simple para extraer el texto limpio de un artículo
    de PubMed Central (PMC) a partir de su PMCID.
    """
    
    def __init__(self, session: Optional[httpx.AsyncClient] = None):
        self._session = session

    def _get_url(self, pmcid: str) -> str:
        if pmcid.upper().startswith("PMC"):
            pmcid = pmcid[3:]
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/"

    async def fetch_full_text(self, pmcid: str) -> Optional[str]:
        if BeautifulSoup is None:
            print("PMCCrawler: Dependencias 'beautifulsoup4' y 'lxml' no instaladas.")
            return None

        url = self._get_url(pmcid)
        try:
            async with (self._session or httpx.AsyncClient(timeout=15.0)) as client:
                r = await client.get(url, follow_redirects=True)
                r.raise_for_status()
                html = r.text
            
            soup = BeautifulSoup(html, 'lxml')
            
            article_body = soup.find('div', id='__article-body')
            if not article_body:
                article_body = soup.find('div', class_='jig-ncbi-article-body')
            
            if not article_body:
                print(f"PMCCrawler: No se encontró 'article-body' en {url}")
                return None

            text_blocks = []
            for element in article_body.find_all(['h2', 'h3', 'p', 'div']):
                if element.name in ('h2', 'h3'):
                    text_blocks.append(f"\n\n## {element.get_text(strip=True)}\n\n")
                elif element.name == 'p':
                    text_blocks.append(element.get_text(strip=True))
                elif 'class' in element.attrs and 'p' in element.attrs['class']:
                    text_blocks.append(element.get_text(strip=True))

            full_text = " ".join(text_blocks)
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            
            return full_text

        except Exception as e:
            print(f"PMCCrawler: Error descargando o parseando {url}: {e}")
            return None

# --- ¡CAMBIO REALIZADO AQUÍ! ---
# Convertido de lambda a def, como ha sugerido el linter (Ruff E731)
def _q_title_exact(title: str) -> str:
    """Formatea una query de búsqueda exacta de título para PubMed."""
    return f"\"{title.replace('\"', '')}\"[Title]"
# --- FIN DEL CAMBIO ---

def _q_title_keywords(text: str, extra: Optional[str] = None) -> str:
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\-]{3,}", text)
    core = " ".join(words[:25]) 
    q = f"({core})[Title/Abstract]"
    if extra:
        q += f" AND ({extra})"
    return q