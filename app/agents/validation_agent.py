from pptx import Presentation
from docx import Document
from app.services.citation_service import extract_citations, normalize
from app.services.fetch_service import fetch_text_for_ref
from app.services.similarity_service import similarity
from app.services.report_service import build_report
import os

class ValidationAgent:
    def validate_file(self, file_path: str, out_pdf: str):
        ext = os.path.splitext(file_path)[1].lower()
        findings = []

        # --- PPTX ---
        if ext == ".pptx":
            prs = Presentation(file_path)
            for i, slide in enumerate(prs.slides, start=1):
                slide_text = []
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        slide_text.append(shape.text)
                text = "\n".join(t for t in slide_text if t).strip()
                if not text:
                    continue
                findings.extend(self._process_text(text, i))

        # --- DOCX ---
        elif ext == ".docx":
            doc = Document(file_path)
            for i, para in enumerate(doc.paragraphs, start=1):
                text = para.text.strip()
                if not text:
                    continue
                findings.extend(self._process_text(text, i))

        else:
            raise ValueError("Formato no soportado: usa .pptx o .docx")

        build_report(file_path, findings, out_pdf)
        summary = {
            "green": sum(1 for f in findings if f["color"] == "green"),
            "yellow": sum(1 for f in findings if f["color"] == "yellow"),
            "red": sum(1 for f in findings if f["color"] == "red"),
            "total": len(findings),
            "report": out_pdf,
        }
        return summary

    # función auxiliar común
    def _process_text(self, text: str, index: int):
        results = []
        refs = [normalize(r) for r in extract_citations(text)]
        for ref in refs:
            src = fetch_text_for_ref(ref)
            score, color = similarity(text, src or "")
            results.append({
                "slide": index,
                "claim": text,
                "ref_raw": ref["id"],
                "score": score,
                "color": color,
                "source_excerpt": (src or "")[:1200],
            })
        return results
