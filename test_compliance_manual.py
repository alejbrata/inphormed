import sys
import os
from app.compliance.engine import ComplianceEngine
from app.schemas import Citation

# Mock environment variables if needed
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "") 

def test():
    print("Initializing ComplianceEngine...")
    engine = ComplianceEngine()
    
    claim_text = "Secukinumab (Cosentyx) cura totalmente la hidradenitis supurativa eliminando el 100% de los nódulos en todos los pacientes a la semana 16, siendo un tratamiento completamente seguro y sin efectos secundarios."
    
    print(f"Testing claim: {claim_text}")
    
    report = engine.run_checks(claim=claim_text, citations=[])
    
    print(f"Report Passed: {report.passed}")
    print(f"Report Score: {report.score}")
    print(f"Issues found: {len(report.issues)}")
    
    for issue in report.issues:
        print(f" - [{issue.severity}] {issue.description}: {issue.reason}")

if __name__ == "__main__":
    test()
