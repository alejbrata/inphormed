from __future__ import annotations
import re
from typing import List, Dict

DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s;,)]+", re.IGNORECASE)
PMID_RE = re.compile(r"\bPMID[:\s]*([0-9]{5,9})\b", re.IGNORECASE)
NCT_RE  = re.compile(r"\bNCT[0-9]{8}\b", re.IGNORECASE)
URL_RE  = re.compile(r"https?://[^\s)]+", re.IGNORECASE)

def extract_references(text: str) -> Dict[str, List[str]]:
    t = text or ""
    dois = list({m.group(0).rstrip(".,);") for m in DOI_RE.finditer(t)})
    pmids = list({m.group(1) for m in PMID_RE.finditer(t)})
    ncts = list({m.group(0) for m in NCT_RE.finditer(t)})
    urls = list({u.rstrip(".,);") for u in URL_RE.findall(t)})
    return {"doi": dois, "pmid": pmids, "nct": ncts, "url": urls}
