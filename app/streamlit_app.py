# app/streamlit_app.py

import os
import json
from typing import List, Dict, Any
import streamlit as st
import base64 # <-- ¡Importante!

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
CHAT_ENDPOINT = os.getenv("CHAT_ENDPOINT", "/api/chat")

# --- ¡CORREGIDO! Apuntar a las rutas de 'validation_routes.py' ---
VALIDATE_TEXT_URL = BACKEND_URL + "/api/claims/validate" # (ruta GET)
VALIDATE_PPT_URL = BACKEND_URL + "/api/claims/validate-ppt" # (ruta POST)
# --- FIN DE LA CORRECCIÓN ---

DEFAULT_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SEC", "900"))

CHAT_URL = BACKEND_URL + CHAT_ENDPOINT

st.set_page_config(page_title="Inphormed", layout="wide")

# ─────────────────────────────────────────────────────────────
# Helpers HTTP
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
# Parsers
# ─────────────────────────────────────────────────────────────
def dedupe_keep_order(items: List[str]) -> List[str]:
    seen, out = set(), []
    for x in items:
        x = (x or "").strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

# --- ¡CORREGIDO! ---
# Actualizado para que coincida con la salida de la API "LLM-First"
# que vemos en tu captura de pantalla
def hits_table_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for r in results:
        status = r.get("status", "red")
        color = {"green":"🟢","yellow":"🟡","red":"🔴"}.get(status, "⚪")
        best = f"{r.get('best_score', 0.0):.3f}"
        
        # Parsear la respuesta del Orquestador
        cite = r.get("best_title", "")[:100]
        url_hit = r.get("best_url", "None")
        
        # El "Snippet" es la explicación del Juez (why_short)
        snippet = (r.get("best_verdict") or "error") 
        if r.get("best_verdict") == "insufficient" and r.get("best_score") == 0.0:
            snippet = "insufficient (no paper found)"

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
# --- FIN DE LA CORRECCIÓN ---

# ─────────────────────────────────────────────────────────────
# VISTAS
# ─────────────────────────────────────────────────────────────
def vista_chatbot_hs(timeout_sec: float):
    st.header("Chatbot – Hidradenitis supurativa")
    # ... (Tu lógica de chatbot se queda igual) ...
    # (No la pego aquí para ahorrar espacio, pero no la borres)
    if "chat_hs" not in st.session_state:
        st.session_state.chat_hs = [
            {"role": "assistant", "content": "Hola, ¿en qué te ayudo?"}
        ]
    for m in st.session_state.chat_hs:
        st.chat_message(m["role"]).markdown(m["content"])
    user_msg = st.chat_input("Pregunta o describe tu caso…")
    if user_msg:
        # ... (resto de la lógica del chatbot) ...
        pass


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

    tabs = st.tabs(["Subir PPTX", "Pegar texto"])

    # ——— Subir PPTX -> /api/claims/validate-ppt ———
    with tabs[0]:
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
                    "render_ppt": True # <-- Importante: pedir el PPTX coloreado
                }
                files = {"file": (f.name, f.getvalue(), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
                try:
                    with st.spinner("Validando claims del PPTX… (Esto puede tardar 1-2 minutos)"):
                        data = post_multipart(VALIDATE_PPT_URL, files=files, params=params, timeout_sec=timeout_sec)
                    
                    st.success(f"Archivo: {data['file_name']} — Claims detectados: {data['total_claims']}")
                    rows = hits_table_rows(data.get("results", []))
                    
                    # --- ¡CORRECCIÓN AÑADIDA! ---
                    # Guardar los datos del PPTX anotado en el estado
                    if data.get("annotated_pptx_b64"):
                        st.session_state.pptx_b64_to_download = data["annotated_pptx_b64"]
                        st.session_state.pptx_name_to_download = data.get("annotated_file_name", "validated.pptx")
                    else:
                        st.session_state.pptx_b64_to_download = None
                        st.session_state.pptx_name_to_download = None
                        st.warning("El backend no devolvió un PPTX anotado (render_ppt=True?).")
                    # --- FIN DE LA CORRECCIÓN ---

                    if rows:
                        import pandas as pd
                        df = pd.DataFrame(rows, columns=["Dónde","Semáforo","Score","Claim","Cita","URL","Snippet"])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin resultados.")
                except Exception as e:
                    st.error(f"Error validando PPTX: {e}")

        # --- ¡CORRECCIÓN AÑADIDA! ---
        # Añadir el botón de descarga si los datos existen en el estado
        if st.session_state.get("pptx_b64_to_download"):
            st.divider()
            try:
                # Decodificar Base64
                b64 = st.session_state.pptx_b64_to_download
                pptx_bytes = base64.b64decode(b64)
                
                st.download_button(
                    label="⬇️ Descargar PPTX Anotado (con enlaces)",
                    data=pptx_bytes,
                    file_name=st.session_state.pptx_name_to_download,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    type="primary"
                )
            except Exception as e:
                st.error(f"No se pudo preparar el PPTX para descarga: {e}")
        # --- FIN DE LA CORRECCIÓN ---

    # ——— Pegar texto -> /api/claims/validate ———
    with tabs[1]:
        st.subheader("Validar texto simple")
        claim_in = st.text_area(
            "Claim",
            placeholder="Adalimumab semanal mejora de forma significativa la respuesta clínica (HiSCR)...",
        )
        cita_in = st.text_area(
            "Contexto / Cita",
            placeholder="Kimball AB, Okun MM, Williams DA, et al. Two Phase 3 Trials of Adalimumab...",
        )
        
        if st.button("Validar (texto pegado)"):
            if not claim_in or not cita_in:
                st.warning("Debes rellenar el Claim y la Cita.")
            else:
                st.info("Función de validación de texto simple en desarrollo...")
                # (Aquí iría la llamada a la ruta GET /api/claims/validate
                # usando httpx.get con los 'params')

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

# --- ¡CORRECCIÓN AÑADIDA! ---
# Inicializar el estado de sesión para el botón de descarga
if "pptx_b64_to_download" not in st.session_state:
    st.session_state.pptx_b64_to_download = None
if "pptx_name_to_download" not in st.session_state:
    st.session_state.pptx_name_to_download = None
# --- FIN DE LA CORRECCIÓN ---

# Pasa el timeout a las vistas que lo usan
if pagina == "Chatbot HS":
    PAGES[pagina](DEFAULT_TIMEOUT)
elif pagina == "Validador de claims":
    PAGES[pagina](DEFAULT_TIMEOUT)
else:
    PAGES[pagina]()

st.caption(f"Backend: {BACKEND_URL}")