# app/agents/ui_agent.py
from __future__ import annotations
from typing import Dict, Tuple, List, Optional
import re

# ====== SINÓNIMOS Y FRASES CLAVE ======
WIDGET_SYNONYMS = {
    "chat": [
        "chat", "conversación", "asistente", "bot", "dialogo", "diálogo"
    ],
    "validate": [
        "validar", "verificar", "verificador", "validador",
        "validar material", "verificar material",
        "validar claims", "verificar claims", "claims", "revisar claims",
        "verificar diapositivas", "verificar documento", "verificar ppt", "verificar word"
    ],
    "create": [
        "crear", "generar", "creador", "generador",
        "crear material", "crear contenido", "generar material", "generar contenido"
    ],
}

ACTION_FIRST = ["primero", "arriba", "al principio", "inicio", "antes", "top"]
ACTION_LAST  = ["último", "ultimo", "abajo", "al final", "final", "bottom"]
ACTION_HIDE  = ["oculta", "ocultar", "esconde", "esconder", "quita", "quitar"]
ACTION_SHOW  = ["muestra", "mostrar", "enseña", "enseñar", "pon", "poner", "activar", "activa"]
ACTION_WIDE  = ["ancho", "grande", "amplio", "agranda", "expandir", "expandelo", "expándelo"]
ACTION_NARROW= ["estrecho", "pequeño", "reduce", "reducir", "estrecha"]

# patrones "antes de / después de"
RE_RELATIVE = re.compile(
    r"(?:pon|mueve|coloca|colócalo|colocar|mover|ordenar|ordena)?\s*"
    r"(?P<a>.+?)\s*(?P<rel>antes de|despues de|después de)\s*(?P<b>.+)",
    flags=re.IGNORECASE
)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _ensure_layout(layout: Dict) -> Dict:
    """Asegura estructura mínima de layout."""
    if not layout or "widgets" not in layout or not isinstance(layout["widgets"], list):
        layout = {
            "version": 1,
            "widgets": [
                {"id": "chat", "order": 0, "span": 2, "visible": True},
                {"id": "validate", "order": 1, "span": 2, "visible": True},
                {"id": "create", "order": 2, "span": 2, "visible": True},
            ],
        }
    # corrige órdenes repetidos
    ordered = sorted(layout["widgets"], key=lambda x: x.get("order", 0))
    for i, w in enumerate(ordered):
        w["order"] = i
        w.setdefault("span", 2)
        w.setdefault("visible", True)
    layout["widgets"] = ordered
    return layout


class UIAgent:
    """
    Interpreta comandos en español para reorganizar el layout:
    - "pon verificar claims primero"
    - "mueve chat al final"
    - "pon validar antes de chat"
    - "oculta crear material" / "muestra crear"
    - "agranda chat" / "reduce validar"
    """

    # ---------- resolución de widgets ----------
    def _resolve_widget_id(self, name: str) -> Optional[str]:
        """Devuelve 'chat' | 'validate' | 'create' según sinónimos."""
        name_n = _norm(name)
        for wid, syns in WIDGET_SYNONYMS.items():
            for s in syns:
                if s in name_n:
                    return wid
        # fallback: heurística por coincidencia de tokens
        tokens = set(name_n.split())
        scores = []
        for wid, syns in WIDGET_SYNONYMS.items():
            best = max(
                (len(tokens & set(_norm(s).split())) for s in syns),
                default=0,
            )
            scores.append((best, wid))
        scores.sort(reverse=True)
        if scores and scores[0][0] > 0:
            return scores[0][1]
        return None

    # ---------- utilidades de reordenación ----------
    def _set_order(self, layout: Dict, wid: str, pos: int) -> None:
        widgets = layout["widgets"]
        by_id = {w["id"]: w for w in widgets}
        if wid not in by_id:
            return
        target = by_id[wid]
        ordered = [w for w in widgets if w is not target]
        pos = max(0, min(pos, len(ordered)))
        ordered.insert(pos, target)
        for i, w in enumerate(ordered):
            w["order"] = i
        layout["widgets"] = ordered

    def _move_a_before_b(self, layout: Dict, wid_a: str, wid_b: str) -> None:
        widgets = layout["widgets"]
        by_id = {w["id"]: w for w in widgets}
        if wid_a not in by_id or wid_b not in by_id or wid_a == wid_b:
            return
        ordered = [w for w in widgets if w["id"] != wid_a]
        # insertar 'a' antes de 'b'
        idx_b = [w["id"] for w in ordered].index(wid_b)
        ordered.insert(idx_b, by_id[wid_a])
        for i, w in enumerate(ordered):
            w["order"] = i
        layout["widgets"] = ordered

    def _move_a_after_b(self, layout: Dict, wid_a: str, wid_b: str) -> None:
        widgets = layout["widgets"]
        by_id = {w["id"]: w for w in widgets}
        if wid_a not in by_id or wid_b not in by_id or wid_a == wid_b:
            return
        ordered = [w for w in widgets if w["id"] != wid_a]
        idx_b = [w["id"] for w in ordered].index(wid_b)
        ordered.insert(idx_b + 1, by_id[wid_a])
        for i, w in enumerate(ordered):
            w["order"] = i
        layout["widgets"] = ordered

    # ---------- acciones ----------
    def apply_command(self, layout: Dict, command: str) -> Tuple[Dict, List[str]]:
        """
        Aplica el comando y devuelve (layout_actualizado, notas).
        Notas se usa para debug (el front actual no las muestra).
        """
        layout = _ensure_layout(layout)
        notes: List[str] = []
        cmd = _norm(command)

        # 1) Relativo: "X antes de Y" / "X después de Y"
        m = RE_RELATIVE.search(cmd)
        if m:
            a_txt = _norm(m.group("a"))
            b_txt = _norm(m.group("b"))
            rel   = _norm(m.group("rel"))  # "antes de" | "después de" | "despues de"

            wid_a = self._resolve_widget_id(a_txt)
            wid_b = self._resolve_widget_id(b_txt)

            if wid_a and wid_b:
                if "antes" in rel:
                    self._move_a_before_b(layout, wid_a, wid_b)
                    notes.append(f"{wid_a} → antes de {wid_b}")
                else:
                    self._move_a_after_b(layout, wid_a, wid_b)
                    notes.append(f"{wid_a} → después de {wid_b}")
                return layout, notes  # acción aplicada

        # 2) Extrae candidato de widget del texto
        #    Buscamos la última mención (para frases tipo: "pon verificar claims primero")
        candidate_ids: List[str] = []
        for wid, syns in WIDGET_SYNONYMS.items():
            for s in syns:
                if _norm(s) in cmd:
                    candidate_ids.append(wid)
                    break
        target: Optional[str] = candidate_ids[-1] if candidate_ids else None
        if not target:
            # heurística general
            target = self._resolve_widget_id(cmd)

        widgets = {w["id"]: w for w in layout["widgets"]}
        if target and target in widgets:
            # 2.1 ordenar primero / último
            if any(k in cmd for k in ACTION_FIRST):
                self._set_order(layout, target, 0)
                notes.append(f"{target} → posición 1")
            elif any(k in cmd for k in ACTION_LAST):
                self._set_order(layout, target, len(layout["widgets"]))
                notes.append(f"{target} → última posición")

            # 2.2 visibilidad
            if any(k in cmd for k in ACTION_HIDE):
                widgets[target]["visible"] = False
                notes.append(f"{target} → visible=False")
            elif any(k in cmd for k in ACTION_SHOW):
                widgets[target]["visible"] = True
                notes.append(f"{target} → visible=True")

            # 2.3 tamaño
            if any(k in cmd for k in ACTION_WIDE):
                widgets[target]["span"] = 2
                notes.append(f"{target} → span=2")
            if any(k in cmd for k in ACTION_NARROW):
                widgets[target]["span"] = 1
                notes.append(f"{target} → span=1")

        # Si no se detectó nada, no pasa nada, y devolvemos layout tal cual
        return layout, notes
