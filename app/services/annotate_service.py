# app/services/annotate_service.py
import os
import re
import uuid
from io import BytesIO
from typing import List, Dict, Tuple
from urllib.parse import urlparse # <-- ¡LA IMPORTACIÓN QUE FALTABA!

# --- ¡IMPORTACIONES QUE FALTABAN! ---
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
# --- FIN DE IMPORTACIONES ---


COLOR_RGB = {
    "green":  RGBColor(0, 150, 0),
    "yellow": RGBColor(255, 165, 0),
    "red":    RGBColor(200, 0, 0),
}

DOCX_HILITE = {
    "green":  WD_COLOR_INDEX.BRIGHT_GREEN,
    "yellow": WD_COLOR_INDEX.YELLOW,
    "red":    WD_COLOR_INDEX.PINK,
}

def _build_colors(color: str) -> Tuple[RGBColor, WD_COLOR_INDEX]:
    return COLOR_RGB.get(color, COLOR_RGB["red"]), DOCX_HILITE.get(color, DOCX_HILITE["red"])

def write_snippets_html(base_uid: str, findings: List[Dict]) -> str:
    os.makedirs("outputs/snippets", exist_ok=True)
    path = f"outputs/snippets/snippets_{base_uid}.html"
    rows = []
    for idx, f in enumerate(findings, start=1):
        rows.append(f"""
        <section id="claim-{idx}" style="margin:1rem 0;padding:1rem;border:1px solid #ddd;border-radius:10px">
          <h3>Claim {idx} — {f['color'].upper()} (score={int(f['score'])})</h3>
          <p><b>Texto del slide/bloque:</b><br>{escape_html(f['claim'])}</p>
          <p><b>Extracto fuente:</b><br><pre style="white-space:pre-wrap">{escape_html(f.get('source_excerpt') or '')}</pre></p>
          <p><a href="{f.get('source_url','')}" target="_blank">Abrir paper</a></p>
        </section>
        """)
    html = f"""<!doctype html><html lang="es"><meta charset="utf-8">
      <title>Snippets Inphormed</title>
      <body style="font-family:Arial,sans-serif;max-width:900px;margin:2rem auto">
      <h1>Snippets de evidencias — Inphormed</h1>
      {''.join(rows)}
      </body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

def escape_html(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# ---------------- PPTX ----------------

def annotate_pptx(original_path: str, out_path: str, findings: List[Dict]) -> bytes:
    prs = Presentation(original_path)
    rgb_green, _ = _build_colors("green")
    
    claims_by_slide = {}
    for f in findings:
        claims_by_slide.setdefault(f["slide"], []).append(f)

    for i, slide in enumerate(prs.slides, start=1):
        slide_claims = claims_by_slide.get(i, [])
        if not slide_claims:
            continue

        for shape in slide.shapes:
            if not hasattr(shape, "text_frame") or not shape.has_text_frame:
                continue
            tf = shape.text_frame
            for para in tf.paragraphs:
                for run in para.runs:
                    text_lower = run.text.strip().lower()
                    if not text_lower:
                        continue
                    
                    for idx, f in enumerate(slide_claims, start=1):
                        color = f["color"]
                        rgb, _ = _build_colors(color)
                        
                        # Usamos el 'ref_raw' (título) o 'claim' para encontrar el texto
                        text_to_match = (f.get("ref_raw") or f["claim"]).lower()
                        
                        if _weak_match(text_lower, text_to_match):
                            run.font.color.rgb = rgb
                            run.font.bold = True
                            
                            url = f.get("source_url") # Este es ahora nuestro enlace al /viewer
                            
                            if url:
                                # ¡AQUÍ ESTABA EL ERROR! (Faltaba 'urlparse')
                                parsed_url = urlparse(url)
                                if not parsed_url.scheme and parsed_url.path.startswith("/api"):
                                    # (En producción, esto vendría de una variable de entorno)
                                    url = f"http://localhost:8000{url}"
                                
                                try:
                                    hlink = run.hyperlink
                                    hlink.address = url
                                except Exception:
                                    pass 
                            
                            # Colorear solo el run que coincide, no seguir buscando en él
                            break

    out_buf = BytesIO()
    prs.save(out_buf)
    out_bytes = out_buf.getvalue()
    
    # Escribir en out_path (útil para debug)
    with open(out_path, "wb") as f:
        f.write(out_bytes)
        
    return out_bytes  
  

def _weak_match(text_chunk: str, text_to_find: str) -> bool:
    """Match ligero: comparte ≥3 palabras de 6+ letras O el chunk contiene el inicio del texto"""
    if not text_chunk or not text_to_find:
        return False
    
    # Opción 1: El chunk contiene el inicio del texto (muy común en PPTX)
    if text_chunk.startswith(text_to_find[:50]):
        return True
        
    # Opción 2: Coincidencia de palabras clave
    words_t = {w for w in re.findall(r"[a-záéíóúñ]{6,}", text_chunk) }
    words_c = {w for w in re.findall(r"[a-záéíóúñ]{6,}", text_to_find)}
    if not words_c:
         return False
    return len(words_t.intersection(words_c)) >= 3

# ---------------- DOCX ----------------
# (Sin cambios, pero lo incluimos para que el archivo esté completo)

def annotate_docx(original_path: str, out_path: str, findings: List[Dict]) -> str:
    doc = Document(original_path)
    for para in doc.paragraphs:
        ptext = para.text.strip().lower()
        if not ptext:
            continue
        for idx, f in enumerate(findings, start=1):
            claim = (f.get("ref_raw") or f["claim"] or "").lower()
            if not _weak_match(ptext, claim):
                continue
            
            _, hi = _build_colors(f["color"])
            for run in para.runs:
                run.font.highlight_color = hi
                run.font.bold = True
            
            url = f.get("source_url")
            if url:
                 # (Lógica de enlace DOCX)
                para.add_run(" [ver evidencia]").font.underline = True
                
    doc.save(out_path)
    return out_path