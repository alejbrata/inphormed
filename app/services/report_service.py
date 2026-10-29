from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from typing import List, Dict

COLOR_MAP = {
    "green": colors.green,
    "yellow": colors.orange,
    "red": colors.red,
}

def draw_wrapped_text(c, text, x, y, max_width, leading=14):
    # simple wrapping
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    style = getSampleStyleSheet()["Normal"]
    style.leading = leading
    p = Paragraph(text.replace("\n","<br/>"), style)
    w, h = p.wrap(max_width, 1000)
    p.drawOn(c, x, y - h)
    return h

def build_report(file_in: str, results: List[Dict], outfile: str):
    c = canvas.Canvas(outfile, pagesize=A4)
    width, height = A4

    # portada
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, height-3*cm, "Informe de validación de claims — Inphormed")
    c.setFont("Helvetica", 11)
    c.drawString(2*cm, height-4*cm, f"Archivo: {file_in}")
    c.drawString(2*cm, height-4.6*cm, "Código de colores: Verde=similar, Amarillo=dudoso, Rojo=no coincide")
    c.showPage()

    # por cada hallazgo
    for item in results:
        slide = item["slide"]
        claim = item["claim"][:800]
        ref   = item["ref_raw"]
        score = item["score"]
        color = item["color"]
        src_excerpt = (item.get("source_excerpt") or "")[:800]

        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(COLOR_MAP[color])
        c.drawString(2*cm, height-2.5*cm, f"Slide {slide} — {color.upper()} (score={int(score)})")
        c.setFillColor(colors.black)
        y = height-4*cm

        c.setFont("Helvetica-Bold", 11)
        c.drawString(2*cm, y, "Texto del slide:")
        y -= 0.6*cm
        h = draw_wrapped_text(c, claim, 2*cm, y, width-4*cm); y -= (h/1.2 + 0.6*cm)

        c.setFont("Helvetica-Bold", 11)
        c.drawString(2*cm, y, "Referencia detectada:")
        y -= 0.6*cm
        h = draw_wrapped_text(c, ref, 2*cm, y, width-4*cm); y -= (h/1.2 + 0.6*cm)

        if src_excerpt:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2*cm, y, "Extracto de la fuente:")
            y -= 0.6*cm
            h = draw_wrapped_text(c, src_excerpt, 2*cm, y, width-4*cm); y -= (h/1.2 + 0.6*cm)

        c.showPage()

    c.save()
