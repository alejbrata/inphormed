# streamlit_app.py  (versión completa con timeout configurable)

import os
import json
from typing import List, Dict, Any
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Config (por ENV si no es localhost:8000)
# ─────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
CHAT_ENDPOINT = os.getenv("CHAT_ENDPOINT", "/api/chat")
CLAIMS_VALIDATE_TEXT = os.getenv("CLAIMS_VALIDATE_TEXT", "/api/claims/validate-text")
CLAIMS_VALIDATE_PPT = os.getenv("CLAIMS_VALIDATE_PPT", "/api/claims/validate-ppt")
DEFAULT_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SEC", "900"))  # ← por defecto 900s

CHAT_URL = BACKEND_URL + CHAT_ENDPOINT
VALIDATE_TEXT_URL = BACKEND_URL + CLAIMS_VALIDATE_TEXT
VALIDATE_PPT_URL = BACKEND_URL + CLAIMS_VALIDATE_PPT

st.set_page_config(page_title="Inphormed", layout="wide")

# ─────────────────────────────────────────────────────────────
# Helpers HTTP (con timeout configurable)
# ─────────────────────────────────────────────────────────────
def post_json(url: str, payload: Dict[str, Any], timeout_sec: float) -> Dict[str, Any]:
    import requests
    r = requests.post(url, json=payload, timeout=timeout_sec)
    r.raise_for_status()
    return r.json()

def post_multipart(url: str, files: Dict[str, Any], params: Dict[str, Any], timeout_sec: float) -> Dict[str, Any]:
    import requests
    r = requests.post(url, files=files, params=params, timeout=timeout_sec)
    r.raise_for_status()
    return r.json()

# ─────────────────────────────────────────────────────────────
# Parsers mínimos (para previsualización local)
# ─────────────────────────────────────────────────────────────
def parse_docx(file_bytes: bytes) -> List[str]:
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(file_bytes))
        lines = []
        for p in doc.paragraphs:
            t = (p.text or "").strip()
            if t:
                lines.append(t)
        return lines
    except Exception as e:
        return [f"[ERROR DOCX] {e}"]

def parse_pptx(file_bytes: bytes) -> List[str]:
    try:
        from pptx import Presentation
        import io
        pres = Presentation(io.BytesIO(file_bytes))
        lines = []
        for slide in pres.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text_frame") and shape.text_frame:
                    txt = (shape.text_frame.text or "").strip()
                    if txt:
                        lines.append(txt)
        return lines
    except Exception as e:
        return [f"[ERROR PPTX] {e}"]

def dedupe_keep_order(items: List[str]) -> List[str]:
    seen, out = set(), []
    for x in items:
        x = (x or "").strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def hits_table_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for r in results:
        status = r.get("status", "red")
        color = {"green":"🟢","yellow":"🟡","red":"🔴"}.get(status, "⚪")
        best = f"{r.get('best_score', 0.0):.3f}"
        first = (r.get("hits") or [{}])[0]
        cite = first.get("pmid") or first.get("doi") or ""
        url_hit = first.get("url") or ""
        snippet = (first.get("text") or "")[:200]
        rows.append({
            "Dónde": r.get("where", ""),
            "Semáforo": f"{color} {status}",
            "Score": best,
            "Claim": (r.get("text") or "")[:120] + ("…" if len(r.get("text") or "")>120 else ""),
            "Cita": cite,
            "URL": url_hit,
            "Snippet": snippet + ("…" if len(snippet)==200 else ""),
        })
    return rows

# ─────────────────────────────────────────────────────────────
# VISTAS
# ─────────────────────────────────────────────────────────────
def vista_chatbot_hs(timeout_sec: float):
    st.header("Chatbot – Hidradenitis supurativa")

    if "chat_hs" not in st.session_state:
        st.session_state.chat_hs = [
            {"role": "assistant", "content": "Hola, ¿en qué te ayudo?"}
        ]

    for m in st.session_state.chat_hs:
        st.chat_message(m["role"]).markdown(m["content"])

    user_msg = st.chat_input("Pregunta o describe tu caso…")
    if user_msg:
        st.session_state.chat_hs.append({"role": "user", "content": user_msg})
        st.chat_message("user").markdown(user_msg)

        messages_for_api: List[Dict[str, str]] = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_hs
            if m["role"] in ("user", "assistant")
        ]
        payload = {"messages": messages_for_api, "topic": "hidradenitis supurativa"}

        try:
            with st.spinner("Pensando…"):
                resp = post_json(CHAT_URL, payload, timeout_sec)
            reply = (resp or {}).get("reply", "").strip() or "No recibí contenido del modelo."
            st.session_state.chat_hs.append({"role": "assistant", "content": reply})
            st.chat_message("assistant").markdown(reply)
        except Exception as e:
            err = f"Error llamando a {CHAT_URL}: {e}"
            st.error(err)
            st.session_state.chat_hs.append({"role": "assistant", "content": err})

def vista_validador_claims(timeout_sec: float):
    st.header("Validador de claims")

    with st.sidebar:
        st.subheader("Parámetros de validación")
        topk = st.number_input("Top-K", min_value=1, max_value=20, value=int(os.getenv("RAG_TOPK", "8")))
        thr_green = st.slider("Umbral verde", 0.0, 1.0, float(os.getenv("RAG_THR_GREEN", "0.82")), 0.01)
        thr_yellow = st.slider("Umbral amarillo", 0.0, 1.0, float(os.getenv("RAG_THR_YELLOW", "0.70")), 0.01)
        st.caption("Rojo si score < amarillo; Amarillo si entre amarillo y verde; Verde si ≥ verde.")
        st.divider()
        st.subheader("Tiempo máximo de espera")
        timeout_sec = st.number_input("Timeout (segundos)", min_value=60, max_value=3600, value=int(timeout_sec), step=30)

    tabs = st.tabs(["Pegar texto", "Subir PPTX"])

    # ——— Pegar texto -> /api/claims/validate-text ———
    with tabs[0]:
        st.subheader("Claims (uno por línea)")
        txt = st.text_area(
            "Pega claims",
            height=180,
            placeholder="Mejora la supervivencia global…\nReducción del 30% frente a SOC…",
        )
        if st.button("Validar (texto pegado)"):
            claims = dedupe_keep_order([line.strip() for line in txt.splitlines() if line.strip()])
            if not claims:
                st.warning("Escribe al menos un claim.")
            else:
                results: List[Dict[str, Any]] = []
                with st.spinner("Validando claims…"):
                    for c in claims:
                        payload = {
                            "text": c,
                            "topk": int(topk),
                            "thr_green": float(thr_green),
                            "thr_yellow": float(thr_yellow),
                            "require_llm": True
                        }
                        try:
                            res = post_json(VALIDATE_TEXT_URL, payload, timeout_sec)
                            results.append(res)
                        except Exception as e:
                            results.append({
                                "where": "text",
                                "text": c,
                                "claim_id": "",
                                "status": "red",
                                "best_score": 0.0,
                                "hits": [],
                                "_error": str(e),
                            })
                rows = hits_table_rows(results)
                if rows:
                    import pandas as pd
                    df = pd.DataFrame(rows, columns=["Dónde","Semáforo","Score","Claim","Cita","URL","Snippet"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Sin resultados.")

    # ——— Subir PPTX -> /api/claims/validate-ppt ———
    with tabs[1]:
        st.subheader("Sube un PPTX con claims")
        f = st.file_uploader("PPTX", type=["pptx"])
        if st.button("Validar (PPTX)", disabled=not f):
            if not f:
                st.warning("Selecciona un PPTX.")
            else:
                params = {
                    "topk": int(topk),
                    "thr_green": float(thr_green),
                    "thr_yellow": float(thr_yellow),
                    "require_llm": True,
                    "render_ppt": True
                }
                files = {"file": (f.name, f.getvalue(), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
                try:
                    with st.spinner("Validando claims del PPTX…"):
                        data = post_multipart(VALIDATE_PPT_URL, files=files, params=params, timeout_sec=timeout_sec)
                    st.success(f"Archivo: {data['file_name']} — Claims detectados: {data['total_claims']}")
                    rows = hits_table_rows(data.get("results", []))
                    if rows:
                        import pandas as pd
                        df = pd.DataFrame(rows, columns=["Dónde","Semáforo","Score","Claim","Cita","URL","Snippet"])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin resultados.")
                except Exception as e:
                    st.error(f"Error validando PPTX: {e}")

def vista_generador_material():
    st.header("Generador de material")
    st.info("Placeholder. Añadiremos plantillas y salida (PDF/PPT) más adelante.")

# ─────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────
PAGES = {
    "Chatbot HS": vista_chatbot_hs,
    "Validador de claims": vista_validador_claims,
    "Generador de material": vista_generador_material,
}

with st.sidebar:
    st.title("Inphormed")
    pagina = st.radio("Menú", list(PAGES.keys()))

# Pasa el timeout a las vistas que lo usan
if pagina == "Chatbot HS":
    PAGES[pagina](DEFAULT_TIMEOUT)
elif pagina == "Validador de claims":
    PAGES[pagina](DEFAULT_TIMEOUT)
else:
    PAGES[pagina]()

st.caption(f"Backend: {BACKEND_URL}")
