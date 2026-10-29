# app/agents/sources/pmc_crawler.py
from __future__ import annotations
import httpx
import re
from typing import Optional

try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class PMCCrawler:
    """
    Agente-Herramienta "Smart Crawler" con capacidad Reader.
    
    Estrategia en cascada:
    1. PMC (PubMed Central): Si hay ID, es la fuente más limpia y estructurada.
    2. Jina Reader (Proxy IA): Para webs complejas (Oxford, NEJM, Elsevier) que usan JS/React.
       Convierte la web a Markdown limpio.
    3. Trafilatura (Local): Fallback si lo anterior falla.
    """
    
    def __init__(self, session: Optional[httpx.AsyncClient] = None):
        self._session = session
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def _get_pmc_url(self, pmcid: str) -> str:
        if pmcid.upper().startswith("PMC"):
            pmcid = pmcid[3:]
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/"

    async def fetch_full_text(self, pmcid: Optional[str], doi: Optional[str] = None) -> Optional[str]:
        # 1. Intento PMC (Prioridad máxima)
        if pmcid:
            print(f"SmartCrawler: Intentando PMC ({pmcid})...")
            text_pmc = await self._fetch_from_pmc(pmcid)
            if text_pmc and len(text_pmc) > 1000:
                return text_pmc
            print(f"SmartCrawler: Falló PMC o texto corto.")

        # 2. Intento Web del Editor (Vía DOI)
        if doi:
            url = f"https://doi.org/{doi}"
            print(f"SmartCrawler: Intentando Web Editor para {doi}...")
            
            # A) Estrategia Jina Reader (Para webs con JS/React como Oxford/NEJM)
            # Jina devuelve Markdown limpio. Es gratis para uso moderado.
            text_reader = await self._fetch_with_reader_api(url)
            if text_reader and len(text_reader) > 1000:
                print("SmartCrawler: ¡Éxito con Reader API!")
                return text_reader
            
            # B) Estrategia Trafilatura (Fallback local)
            print("SmartCrawler: Falló Reader API, intentando Trafilatura local...")
            text_trafilatura = await self._fetch_with_trafilatura(url)
            if text_trafilatura:
                return text_trafilatura

        return None

    async def _fetch_from_pmc(self, pmcid: str) -> Optional[str]:
        """Descarga directa de PMC."""
        if BeautifulSoup is None: return None
        url = self._get_pmc_url(pmcid)
        try:
            async with (self._session or httpx.AsyncClient(timeout=15.0)) as client:
                r = await client.get(url, headers=self.headers, follow_redirects=True)
                if r.status_code != 200: return None
                
                soup = BeautifulSoup(r.text, 'lxml')
                body = soup.find('div', id='__article-body') or soup.find('div', class_='jig-ncbi-article-body')
                if not body: return None

                # Limpieza específica de PMC
                blocks = []
                for tag in body.find_all(['h2', 'h3', 'p']):
                    if tag.name in ('h2', 'h3'):
                        blocks.append(f"\n\n## {tag.get_text(strip=True)}\n\n")
                    else:
                        blocks.append(tag.get_text(strip=True))
                return " ".join(blocks).strip()
        except Exception:
            return None

    async def _fetch_with_reader_api(self, target_url: str) -> Optional[str]:
        """
        Usa r.jina.ai para renderizar la web y extraer el contenido principal.
        Esto salta la mayoría de barreras de Javascript y Popups de cookies.
        """
        # La URL de Jina Reader es simplemente https://r.jina.ai/<URL_DESTINO>
        reader_url = f"https://r.jina.ai/{target_url}"
        
        try:
            async with (self._session or httpx.AsyncClient(timeout=30.0)) as client:
                # Jina a veces tarda un poco en renderizar, damos 30s
                r = await client.get(reader_url, headers=self.headers, follow_redirects=True)
                if r.status_code == 200:
                    text = r.text
                    # Validación básica: si devuelve muy poco o errores de Jina
                    if "Jina Reader" in text[:100] and len(text) < 500:
                        return None
                    return text
                return None
        except Exception as e:
            print(f"SmartCrawler Reader Error: {e}")
            return None

    async def _fetch_with_trafilatura(self, url: str) -> Optional[str]:
        """Fallback local si no queremos/podemos usar API externa."""
        if trafilatura is None: return None
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded: return None
            return trafilatura.extract(
                downloaded, 
                include_comments=False, 
                include_tables=False, 
                include_formatting=True
            )
        except Exception:
            return None

# --- ¡CORREGIDO! (Compatible con Python 3.10/3.11) ---
def _q_title_exact(title: str) -> str:
    # Sacamos la lógica fuera del f-string para evitar backslashes
    clean_title = title.replace('"', '')
    return f'"{clean_title}"[Title]'

def _q_title_keywords(text: str, extra: Optional[str] = None) -> str:
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\-]{3,}", text)
    core = " ".join(words[:25]) 
    q = f"({core})[Title/Abstract]"
    if extra:
        q += f" AND ({extra})"
    return q   