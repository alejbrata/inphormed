import re
from typing import List, Dict, Optional

CITATION_PATTERNS = [
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",              # DOI
    r"\bPMID[:\s]?(\d{6,9})\b",                      # PMID
    r"([A-Z][A-Za-z-]+(?:\set\s?al\.)?)\s*\(?\d{4}\)?", # Autor (et al.) (Año)
]

def extract_citations(text: str) -> List[Dict]:
    results = []
    for pat in CITATION_PATTERNS:
        for m in re.finditer(pat, text, flags=re.I):
            val = m.group(0)
            results.append({"raw": val})
    # dedup simples
    seen, uniq = set(), []
    for r in results:
        k = r["raw"].lower()
        if k not in seen:
            seen.add(k); uniq.append(r)
    return uniq

def normalize(ref: Dict) -> Dict:
    raw = ref["raw"]
    ref["type"] = "unknown"
    if raw.lower().startswith("10."):
        ref.update({"type":"doi", "id":raw})
    elif "pmid" in raw.lower():
        pmid = re.sub(r"\D", "", raw)
        ref.update({"type":"pmid", "id":pmid})
    else:
        ref.update({"type":"author-year", "id":raw})
    return ref
