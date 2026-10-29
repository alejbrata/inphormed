from typing import Protocol, List, Dict, Any, Optional
from app.schemas import Citation, ComplianceIssue

class Rule(Protocol):
    def __call__(self, claim: str, citations: List[Citation], generated_text: Optional[str], meta: Dict[str, Any]) -> ComplianceIssue:
        ...

EMA_RULES: List[Rule] = []
FDA_RULES: List[Rule] = []
ALL_RULES: List[Rule] = []
