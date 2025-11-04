# app/compliance/engine.py
from __future__ import annotations

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

from app.schemas import Citation, ComplianceIssue, ComplianceReport
from app.compliance.checklists import EMA_RULES, FDA_RULES, ALL_RULES, Rule
from app.audit.auditor import Auditor


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
    standard: str = "ALL"         # "EMA" | "FDA" | "ALL"
    score_start: int = 100
    penalties: Dict[str, int] = None
    pass_condition = DEFAULT_PASS_CONDITION

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

    def _rules(self) -> List[Rule]:
        std = (self.config.standard or "ALL").upper()
        if std == "EMA":
            return EMA_RULES
        if std == "FDA":
            return FDA_RULES
        return ALL_RULES

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
        # 1) Ejecutar reglas
        issues: List[ComplianceIssue] = []
        for rule in self._rules():
            issue = rule(claim, citations, generated_text, meta or {})
            issues.append(issue)

        # 2) Calcular score (penalizaciones)
        score = self.config.score_start
        for i in issues:
            if not i.passed:
                score -= int(self.config.penalties.get(i.severity, 0))
        score = max(0, min(100, score))

        # 3) Determinar passed
        passed = bool(self.config.pass_condition(issues))

        report = ComplianceReport(
            standard=self.config.standard.upper(),
            issues=issues,
            score=score,
            passed=passed,
            notes=None,
        )

        # 4) Auditoría (opcional)
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
