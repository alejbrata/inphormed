# app/streamlit_app.py  (versión completa con timeout configurable)

import os
import json
from typing import List, Dict, Any
import streamlit as st
# --- ¡AÑADIDO! ---
import base64 

# ─────────────────────────────────────────────────────────────
# Config (por ENV si no es localhost:8000)
# ─────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
CHAT_ENDPOINT = os.getenv("CHAT_ENDPOINT", "/api/chat")

# --- ¡CAMBIO! ---
# Apuntar a las nuevas rutas unificadas
VALIDATE_TEXT_URL = BACKEND_URL + "/api/claims/validate" # (Era /api/claims/validate-text)
VALIDATE_PPT_URL = BACKEND_URL + "/api/claims/validate-ppt"
# --- FIN CAMBIO ---

DEFAULT_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SEC", "900"))

CHAT_URL = BACKEND_URL + CHAT_ENDPOINT


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

# --- ¡CAMBIO! ---
# (He eliminado los parsers de PPTX/DOCX que ya no se usan aquí)
# ...

def dedupe_keep_order(items: List[str]) -> List[str]:
    seen, out = set(), []
    for x in items:
        x = (x or "").strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

# --- ¡CAMBIO! ---
# Actualizado para que coincida con la salida de la API "LLM-First"
def hits_table_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for r in results:
        status = r.get("status", "red")
        color = {"green":"🟢","yellow":"🟡","red":"🔴"}.get(status, "⚪")
        best = f"{r.get('best_score', 0.0):.3f}"
        
        # El modelo "LLM-First" devuelve 'best_title' y 'best_url'
        cite = r.get("best_title", "")[:100]
        url_hit = r.get("best_url", "")
        snippet = (r.get("best_verdict") or "") # El 'why_short' del Juez
        
        rows.append({
            "Dónde": r.get("where", ""),
            "Semáforo": f"{color} {status}",
            "Score": best,
            "Claim": (r.get("text") or "")[:120] + ("…" if len(r.get("text") or "")>120 else ""),
            "Cita": cite + ("…" if len(cite)==100 else ""),
            "URL": url_hit,
            "Snippet": snippet,
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

    # ——— Pegar texto -> /api/claims/validate ———
    with tabs[0]:
        st.subheader("Claims (uno por línea)")
        txt = st.text_area(
            "Pega claims",
            height=180,
            placeholder="Claim: Mejora la supervivencia global…\nCita: Autor et al. 2023...",
        )
        if st.button("Validar (texto pegado)"):
            claims = dedupe_keep_order([line.strip() for line in txt.splitlines() if line.strip()])
            if not claims:
                st.warning("Escribe al menos un claim.")
            else:
                st.info("Función no implementada en este flujo (usar PPTX)")
                # (La lógica de 'validate-text' ahora es '/validate' (GET)
                # y requiere 'claim_text' y 'slide_excerpt' por separado,
                # por lo que este text_area simple ya no es compatible.)

    # ——— Subir PPTX -> /api/claims/validate-ppt ———
    with tabs[1]:
        st.subheader("Sube un PPTX con claims")
        f = st.file_uploader("PPTX", type=["pptx"])
        
        # Limpiar el botón de descarga si se sube un nuevo archivo
        if f:
            st.session_state.pptx_b64_to_download = None
            st.session_state.pptx_name_to_download = None

        if st.button("Validar (PPTX)", disabled=not f):
            if not f:
                st.warning("Selecciona un PPTX.")
            else:
                params = {
                    "topk": int(topk),
                    "thr_green": float(thr_green),
                    "thr_yellow": float(thr_yellow),
                    "render_ppt": True
                }
                files = {"file": (f.name, f.getvalue(), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
                try:
                    with st.spinner("Validando claims del PPTX… (Esto puede tardar 1-2 minutos)"):
                        data = post_multipart(VALIDATE_PPT_URL, files=files, params=params, timeout_sec=timeout_sec)
                    
                    st.success(f"Archivo: {data['file_name']} — Claims detectados: {data['total_claims']}")
                    rows = hits_table_rows(data.get("results", []))
                    
                    # --- ¡CAMBIO REALIZADO AQUÍ! ---
                    # Guardar los datos del PPTX anotado en el estado
                    if data.get("annotated_pptx_b64"):
                        st.session_state.pptx_b64_to_download = data["annotated_pptx_b64"]
                        st.session_state.pptx_name_to_download = data.get("annotated_file_name", "validated.pptx")
                    else:
                        st.session_state.pptx_b64_to_download = None
                        st.session_state.pptx_name_to_download = None
                    # --- FIN DEL CAMBIO ---

                    if rows:
                        import pandas as pd
                        df = pd.DataFrame(rows, columns=["Dónde","Semáforo","Score","Claim","Cita","URL","Snippet"])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin resultados.")
                except Exception as e:
                    st.error(f"Error validando PPTX: {e}")

        # --- ¡CAMBIO REALIZADO AQUÍ! ---
        # Añadir el botón de descarga si los datos existen en el estado
        if st.session_state.get("pptx_b64_to_download"):
            st.divider()
            try:
                # Decodificar Base64
                b64 = st.session_state.pptx_b64_to_download
                pptx_bytes = base64.b64decode(b64)
                
                st.download_button(
                    label="⬇️ Descargar PPTX Anotado",
                    data=pptx_bytes,
                    file_name=st.session_state.pptx_name_to_download,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    type="primary"
                )
            except Exception as e:
                st.error(f"No se pudo preparar el PPTX para descarga: {e}")
        # --- FIN DEL CAMBIO ---


def vista_generador_material():
    st.header("Generador de material")
    st.info("Placeholder. Añadiremos plantillas y salida (PDF/PPT) más adelante.")

# ─────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────
PAGES = {
    "Validador de claims": vista_validador_claims,
    "Chatbot HS": vista_chatbot_hs,
    "Generador de material": vista_generador_material,
}

with st.sidebar:
    st.title("Inphormed")
    pagina = st.radio("Menú", list(PAGES.keys()))

# Inicializar estado para el botón de descarga
if "pptx_b64_to_download" not in st.session_state:
    st.session_state.pptx_b64_to_download = None
if "pptx_name_to_download" not in st.session_state:
    st.session_state.pptx_name_to_download = None

# Pasa el timeout a las vistas que lo usan
if pagina == "Chatbot HS":
    PAGES[pagina](DEFAULT_TIMEOUT)
elif pagina == "Validador de claims":
    PAGES[pagina](DEFAULT_TIMEOUT)
else:
    PAGES[pagina]()

st.caption(f"Backend: {BACKEND_URL}")