# app/orchestrator/orchestrator.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List
import threading

from app.agents.base import AgenteFuente
from app.schemas import ResultadoFuente


class Orquestador:
    """
    Coordina la búsqueda de evidencia para un claim lanzando varios AgenteFuente en modo carrera.
    - Ejecuta los agentes en paralelo.
    - El primer ResultadoFuente válido "gana".
    - Señal de cancelación cooperativa para el resto.
    - Respeta un timeout global por claim.

    No realiza embeddings ni indexa; solo coordina agentes. La ingesta vendrá después.
    """

    def __init__(self, agentes: Optional[List[AgenteFuente]] = None):
        # Puedes inyectar la lista desde fuera; si no, se podrá setear luego con set_agentes()
        self._agentes: List[AgenteFuente] = agentes or []

    def set_agentes(self, agentes: List[AgenteFuente]) -> None:
        """Registra o sustituye los agentes activos."""
        self._agentes = agentes

    def resolver_claim(self, claim: str, timeout_seconds: int = 8) -> Optional[ResultadoFuente]:
        """
        Lanza la carrera entre agentes y devuelve el primer ResultadoFuente válido.
        Si ninguno llega a tiempo o aportan None, devuelve None.
        """
        if not self._agentes:
            return None

        deadline = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        cancel_event = threading.Event()
        winner_lock = threading.Lock()
        winner: dict = {"res": None}

        def run_agent(agent: AgenteFuente):
            # Cada agente intentará buscar hasta deadline. Debe internamente usar timeouts de red.
            res = agent.buscar(claim, deadline)
            if res is not None and not cancel_event.is_set():
                # Ganador provisional: fija resultado y cancela al resto
                with winner_lock:
                    if winner["res"] is None:
                        winner["res"] = res
                        cancel_event.set()

        threads: List[threading.Thread] = []
        for a in self._agentes:
            t = threading.Thread(target=run_agent, args=(a,), daemon=True)
            t.start()
            threads.append(t)

        # Espera acotada (deadline) a que alguno gane o a que todos terminen
        remaining = max(0.0, (deadline - datetime.utcnow()).total_seconds())
        for t in threads:
            t.join(timeout=remaining)

        return winner["res"]
