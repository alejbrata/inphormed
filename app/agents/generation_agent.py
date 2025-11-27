from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from app.services.llm_service import LLMService
from typing import Dict, Any
import io
import pypdf
import docx

class GenerationAgent:
    def __init__(self):
        self.llm = LLMService()
        # Theme Colors
        self.COLOR_PRIMARY = RGBColor(79, 70, 229)    # Indigo 600
        self.COLOR_SECONDARY = RGBColor(13, 148, 136) # Teal 600
        self.COLOR_BG = RGBColor(248, 250, 252)       # Slate 50
        self.COLOR_TEXT = RGBColor(30, 41, 59)        # Slate 800
        self.COLOR_ACCENT = RGBColor(99, 102, 241)    # Indigo 500

    def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        text = ""
        if filename.lower().endswith('.pdf'):
            try:
                pdf_file = io.BytesIO(file_content)
                reader = pypdf.PdfReader(pdf_file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            except Exception as e:
                print(f"Error extracting PDF: {e}")
                raise ValueError("Error al procesar el archivo PDF.")
        elif filename.lower().endswith('.docx'):
            try:
                docx_file = io.BytesIO(file_content)
                doc = docx.Document(docx_file)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            except Exception as e:
                print(f"Error extracting DOCX: {e}")
                raise ValueError("Error al procesar el archivo Word.")
        else:
            # Try as plain text
            try:
                text = file_content.decode('utf-8')
            except:
                raise ValueError("Formato de archivo no soportado. Usa PDF, DOCX o Texto.")
        
        return text.strip()

    def _apply_slide_formatting(self, slide, title_text, is_title_slide=False):
        # Set Background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.COLOR_BG

        # Format Title
        if slide.shapes.title:
            title = slide.shapes.title
            title.text = title_text
            
            # Position title (except for title slide which has its own layout)
            if not is_title_slide:
                title.top = Inches(0.5)
                title.left = Inches(0.5)
                title.width = Inches(9)
                title.height = Inches(1.0)

            for paragraph in title.text_frame.paragraphs:
                paragraph.font.name = 'Calibri'
                paragraph.font.size = Pt(44) if is_title_slide else Pt(32)
                paragraph.font.bold = True
                paragraph.font.color.rgb = self.COLOR_PRIMARY
                paragraph.alignment = PP_ALIGN.CENTER if is_title_slide else PP_ALIGN.LEFT

        # Add Decorative Element (Top Bar)
        if not is_title_slide:
            shape = slide.shapes.add_shape(
                1, # msoShapeRectangle
                Inches(0), Inches(0), Inches(10), Inches(0.15)
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = self.COLOR_SECONDARY
            shape.line.fill.background() # No line

        # Add Footer
        footer = slide.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(9), Inches(0.5))
        tf = footer.text_frame
        p = tf.paragraphs[0]
        p.text = "Inphormed AI • Generado automáticamente"
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor(148, 163, 184) # Slate 400
        p.alignment = PP_ALIGN.CENTER

    def generate_presentation(self, text: str, num_slides: int) -> bytes:
        # 1. Obtener estructura JSON del LLM
        structure = self._get_presentation_structure(text, num_slides)
        
        # 2. Crear PPTX
        prs = Presentation()
        
        # --- Slide 1: Título ---
        title_slide_layout = prs.slide_layouts[0] # Title Slide
        slide = prs.slides.add_slide(title_slide_layout)
        
        title_text = structure.get("title", "Presentación Generada")
        self._apply_slide_formatting(slide, title_text, is_title_slide=True)
        
        # Subtitle
        if slide.placeholders[1]:
            subtitle = slide.placeholders[1]
            subtitle.text = "Generado por Inphormed AI"
            for paragraph in subtitle.text_frame.paragraphs:
                paragraph.font.size = Pt(20)
                paragraph.font.color.rgb = self.COLOR_SECONDARY

        # --- Slides de Contenido ---
        bullet_slide_layout = prs.slide_layouts[1] # Title and Content
        
        for slide_data in structure.get("slides", []):
            slide = prs.slides.add_slide(bullet_slide_layout)
            
            # Apply formatting and title
            self._apply_slide_formatting(slide, slide_data.get("title", "Sin Título"))
            
            # Content Body
            if slide.placeholders[1]:
                body_shape = slide.placeholders[1]
                body_shape.top = Inches(1.5)
                body_shape.left = Inches(0.5)
                body_shape.width = Inches(9)
                body_shape.height = Inches(5.0)

                tf = body_shape.text_frame
                tf.word_wrap = True
                
                points = slide_data.get("points", [])
                if points:
                    tf.text = points[0]
                    p = tf.paragraphs[0]
                    p.font.size = Pt(18)
                    p.font.color.rgb = self.COLOR_TEXT
                    p.space_after = Pt(14)

                    for point in points[1:]:
                        p = tf.add_paragraph()
                        p.text = point
                        p.font.size = Pt(18)
                        p.font.color.rgb = self.COLOR_TEXT
                        p.space_after = Pt(14)
                        p.level = 0

        # 3. Guardar en buffer
        output = io.BytesIO()
        prs.save(output)
        output.seek(0)
        return output.read()

    def _get_presentation_structure(self, text: str, num_slides: int) -> Dict[str, Any]:
        """
        Usa el LLM para estructurar el contenido en diapositivas.
        """
        system_prompt = f"""
        Eres un experto en comunicación científica.
        Tu tarea es transformar un texto técnico en una estructura para una presentación de PowerPoint de {num_slides} diapositivas.
        
        Formato JSON requerido:
        {{
          "title": "Título Principal de la Presentación",
          "slides": [
            {{
              "title": "Título de la Diapositiva 1 (ej. Objetivo)",
              "points": ["Punto clave 1", "Punto clave 2", "Punto clave 3"]
            }},
            ...
          ]
        }}
        
        Reglas:
        - Genera EXACTAMENTE {num_slides} diapositivas de contenido (sin contar la portada).
        - Cada diapositiva debe tener entre 3 y 5 puntos clave (bullets).
        - Sé conciso y directo.
        """
        
        # Truncar texto
        max_chars = 15000
        truncated_text = text[:max_chars] + "..." if len(text) > max_chars else text
        
        user_prompt = f"Genera la estructura de la presentación basada en este texto:\n\n{truncated_text}"
        
        data = self.llm.chat_with_json(system_prompt, user_prompt)
        
        if not data or "slides" not in data:
             # Fallback simple si falla el JSON
             return {
                 "title": "Resumen Automático",
                 "slides": [
                     {"title": "Error de Generación", "points": ["No se pudo estructurar el contenido correctamente."]}
                 ]
             }
             
        return data
