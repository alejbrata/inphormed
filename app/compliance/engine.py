# app/compliance/engine.py
from __future__ import annotations

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import os
import json

from app.schemas import Citation, ComplianceIssue, ComplianceReport
from app.compliance.checklists import EMA_RULES, FDA_RULES, ALL_RULES, Rule
from app.audit.auditor import Auditor
from app.services.llm_service import LLMService
from app.llm.prompts_compliance import SYSTEM_PROMPT_COMPLIANCE, build_compliance_prompt


# ----------------- Ponderaciones / Umbrales -----------------
SEVERITY_PENALTY = {
    "critical": 40,
    "major": 20,
    "minor": 5,
    "info": 0,
}

# Passed si: sin fallos critical/major (configurable)
DEFAULT_PASS_CONDITION = lambda issues: not any((not i.passed and i.severity in ("critical", "major")) for i in issues)


@dataclass
class ComplianceConfig:
    standard: str = "ALL"         # "EMA" | "FDA" | "ALL" | "FARMAINDUSTRIA"
    score_start: int = 100
    penalties: Dict[str, int] = None
    pass_condition = DEFAULT_PASS_CONDITION
    use_llm: bool = True

    def __post_init__(self):
        if self.penalties is None:
            self.penalties = SEVERITY_PENALTY


class ComplianceEngine:
    """
    Ejecuta reglas de compliance para un claim/material y devuelve ComplianceReport.
    Inputs mínimos:
      - claim: str
      - citations: List[Citation]    (idealmente con doc_hash y chunk_hash)
    Opcionales:
      - generated_text: str          (texto del material promocional propuesto)
      - meta: dict                   (p. ej., approved_indications)
      - auditor: Auditor             (para loguear la decisión)
    """

    def __init__(self, config: Optional[ComplianceConfig] = None, auditor: Optional[Auditor] = None):
        self.config = config or ComplianceConfig()
        self.auditor = auditor  # opcional
        self.llm_service = None
        
        if self.config.use_llm:
            try:
                self.llm_service = LLMService(
                    model=os.getenv("OPENAI_COMPLIANCE_MODEL", "gpt-4o-mini"),
                    temperature=0.0
                )
            except Exception as e:
                print(f"WARN: No se pudo iniciar LLMService para Compliance: {e}")

    def _rules(self) -> List[Rule]:
        std = (self.config.standard or "ALL").upper()
        if std == "EMA":
            return EMA_RULES
        if std == "FDA":
            return FDA_RULES
        # Si es Farmaindustria, quizás no queramos reglas estáticas, o sí.
        # Por ahora devolvemos ALL_RULES como base si no es específico.
        return ALL_RULES

    def _check_farmaindustria_llm(self, claim: str) -> Optional[ComplianceIssue]:
        if not self.llm_service:
            return None

        try:
            prompt = build_compliance_prompt(claim)
            response = self.llm_service.chat_with_json(
                system_prompt=SYSTEM_PROMPT_COMPLIANCE,
                user_prompt=prompt
            )
            
            if not response:
                return None

            is_compliant = response.get("compliant", True)
            if not is_compliant:
                article = response.get("violation_article", "Unknown Article")
                reason = response.get("reason", "No reason provided")
                
                return ComplianceIssue(
                    rule_id="FARMA_LLM_01",
                    description=f"Farmaindustria Check: {article}",
                    severity="critical", # Farmaindustria suele ser crítico
                    passed=False,
                    reason=f"{article}: {reason}"
                )
            
            return ComplianceIssue(
                rule_id="FARMA_LLM_01",
                description="Farmaindustria Check",
                severity="info",
                passed=True,
                reason="Cumple con la normativa analizada."
            )

        except Exception as e:
            print(f"Error en Compliance LLM: {e}")
            return None

    def run_checks(
        self,
        *,
        claim: str,
        citations: List[Citation],
        generated_text: Optional[str] = None,
        meta: Optional[dict] = None,
        intake_id: Optional[str] = None,
        claim_id: Optional[str] = None,
    ) -> ComplianceReport:
        # 1) Ejecutar reglas estáticas (legacy)
        issues: List[ComplianceIssue] = []
        # Solo ejecutamos reglas estáticas si NO es solo Farmaindustria o si queremos mezclar
        if self.config.standard != "FARMAINDUSTRIA":
            for rule in self._rules():
                issue = rule(claim, citations, generated_text, meta or {})
                issues.append(issue)

        # 2) Ejecutar LLM Check (Farmaindustria)
        # Lo ejecutamos siempre si está habilitado, o específicamente si el standard lo pide
        if self.config.use_llm:
            llm_issue = self._check_farmaindustria_llm(claim)
            if llm_issue:
                issues.append(llm_issue)

        # 3) Calcular score (penalizaciones)
        score = self.config.score_start
        for i in issues:
            if not i.passed:
                score -= int(self.config.penalties.get(i.severity, 0))
        score = max(0, min(100, score))

        # 4) Determinar passed
        # FIX: Call lambda directly to avoid method binding issues
        passed = bool(DEFAULT_PASS_CONDITION(issues))

        report = ComplianceReport(
            standard=self.config.standard.upper(),
            issues=issues,
            score=score,
            passed=passed,
            notes=None,
        )

        # 5) Auditoría (opcional)
        if self.auditor:
            self.auditor.log_event(
                "ComplianceReport",
                intake_id=intake_id or "-",
                claim_id=claim_id or "-",
                data={
                    "standard": report.standard,
                    "score": report.score,
                    "passed": report.passed,
                    "issues": [i.model_dump() for i in report.issues],
                },
            )

        return report
