import os
import uuid
from typing import List, Tuple, Dict, Any
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from app.services.llm_service import LLMService
import io
import fitz  # PyMuPDF
import docx
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.lib.units import inch
from reportlab.lib import utils

class GenerationAgent:
    def __init__(self):
        self.llm = LLMService()
        # Pharma Corporate Colors
        self.COLOR_PRIMARY = RGBColor(0, 51, 102)     # Navy Blue (Trust/Authority)
        self.COLOR_SECONDARY = RGBColor(0, 114, 206)  # Medical Blue (Innovation)
        self.COLOR_BG = RGBColor(255, 255, 255)       # White
        self.COLOR_TEXT = RGBColor(51, 51, 51)        # Dark Grey (Readability)
        self.COLOR_LIGHT_BG = RGBColor(240, 242, 245) # Soft Grey (Backgrounds)
        self.FONT_NAME = 'Arial' # Clean, standard sans-serif

    def extract_text_from_file(self, file_content: bytes, filename: str) -> Tuple[str, List[str]]:
        """
        Extrae texto e imágenes de un archivo usando PyMuPDF (fitz).
        Retorna: (texto_completo, lista_de_rutas_a_imagenes_temporales)
        """
        text = ""
        image_paths = []
        
        if filename.lower().endswith('.pdf'):
            try:
                # Abrir PDF desde memoria
                pdf_document = fitz.open(stream=file_content, filetype="pdf")
                
                # Crear directorio temporal para imágenes si no existe
                temp_img_dir = os.path.join(os.getcwd(), "temp_images")
                os.makedirs(temp_img_dir, exist_ok=True)

                for page_index in range(len(pdf_document)):
                    page = pdf_document[page_index]
                    text += page.get_text() + "\n"
                    
                    # Extraer imágenes
                    image_list = page.get_images(full=True)
                    
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            base_image = pdf_document.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            
                            # Filtrar imágenes muy pequeñas (iconos, líneas)
                            if len(image_bytes) < 2048: # < 2KB
                                continue

                            img_name = f"{uuid.uuid4().hex}.{image_ext}"
                            img_path = os.path.join(temp_img_dir, img_name)
                            
                            with open(img_path, "wb") as fp:
                                fp.write(image_bytes)
                            
                            image_paths.append(img_path)
                            
                            # Limitar a 15 imágenes para no saturar
                            if len(image_paths) >= 15:
                                break
                        except Exception as e:
                            print(f"Error extrayendo imagen {img_index} en pág {page_index}: {e}")
                    
                    if len(image_paths) >= 15:
                        break

            except Exception as e:
                print(f"Error extracting PDF with Fitz: {e}")
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
            try:
                text = file_content.decode('utf-8')
            except:
                raise ValueError("Formato de archivo no soportado. Usa PDF, DOCX o Texto.")
        
        return text.strip(), image_paths

    def _apply_theme(self, slide, is_title_slide=False):
        """Aplica elementos de diseño geométrico y fondo."""
        # Fondo
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.COLOR_BG
        
        # Elementos Geométricos
        if is_title_slide:
            # Banda lateral izquierda grande (Navy)
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(3.0), Inches(7.5)
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = self.COLOR_PRIMARY
            shape.line.fill.background()
            
            # Acento Medical Blue
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(3.0), Inches(0), Inches(0.15), Inches(7.5)
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = self.COLOR_SECONDARY
            shape.line.fill.background()
            
        else:
            # Header Bar Clean (Navy)
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(10), Inches(0.1)
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = self.COLOR_PRIMARY
            shape.line.fill.background()
            
            # Footer Accent (Medical Blue)
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(0), Inches(7.4), Inches(10), Inches(0.1)
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = self.COLOR_SECONDARY
            shape.line.fill.background()

        # Footer Text
        footer = slide.shapes.add_textbox(Inches(0.5), Inches(7.1), Inches(9), Inches(0.3))
        tf = footer.text_frame
        p = tf.paragraphs[0]
        p.text = "Inphormed AI • Generado automáticamente"
        p.font.size = Pt(9)
        p.font.name = self.FONT_NAME
        p.font.color.rgb = RGBColor(128, 128, 128)
        p.alignment = PP_ALIGN.RIGHT

    def _create_dashboard_slide(self, prs, data):
        """Crea una diapositiva estilo Dashboard Ejecutivo (One-Pager)."""
        slide_layout = prs.slide_layouts[6] # Blank
        slide = prs.slides.add_slide(slide_layout)
        self._apply_theme(slide, is_title_slide=False)

        # 1. Header Corporativo
        # Title
        title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(1.0))
        tf = title_shape.text_frame
        p = tf.paragraphs[0]
        p.text = data.get("title", "Executive Summary").upper()
        p.font.name = self.FONT_NAME
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = self.COLOR_PRIMARY
        
        # Main Insight (Subtitle)
        subtitle_shape = slide.shapes.add_textbox(Inches(0.5), Inches(1.0), Inches(9), Inches(0.8))
        tf = subtitle_shape.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = data.get("main_insight", "")
        p.font.name = self.FONT_NAME
        p.font.size = Pt(16)
        p.font.italic = True
        p.font.color.rgb = self.COLOR_SECONDARY

        # 2. Key Stats (Right Column - 3 Circles)
        stats = data.get("key_stats", [])
        y_pos = 2.0
        for stat in stats[:3]: # Max 3 stats
            # Circle Background
            oval = slide.shapes.add_shape(
                MSO_SHAPE.OVAL, Inches(7.0), Inches(y_pos), Inches(2.2), Inches(2.2)
            )
            oval.fill.solid()
            oval.fill.fore_color.rgb = self.COLOR_PRIMARY
            oval.line.fill.background()

            # Value
            val_shape = slide.shapes.add_textbox(Inches(7.0), Inches(y_pos + 0.6), Inches(2.2), Inches(0.8))
            tf = val_shape.text_frame
            p = tf.paragraphs[0]
            p.text = stat.get("value", "")
            p.font.name = self.FONT_NAME
            p.font.size = Pt(36)
            p.font.bold = True
            p.font.color.rgb = self.COLOR_BG
            p.alignment = PP_ALIGN.CENTER

            # Label
            label_shape = slide.shapes.add_textbox(Inches(7.2), Inches(y_pos + 1.3), Inches(1.8), Inches(0.6))
            tf = label_shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = stat.get("label", "")
            p.font.name = self.FONT_NAME
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = self.COLOR_SECONDARY
            p.alignment = PP_ALIGN.CENTER
            
            y_pos += 2.4

        # 3. Key Takeaways (Left Column)
        takeaways_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.0), Inches(6.0), Inches(4.5))
        tf = takeaways_box.text_frame
        tf.word_wrap = True
        
        # Header for Takeaways
        p = tf.paragraphs[0]
        p.text = "HALLAZGOS CLAVE"
        p.font.name = self.FONT_NAME
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = self.COLOR_SECONDARY
        p.space_after = Pt(10)

        for point in data.get("takeaways", []):
            p = tf.add_paragraph()
            p.text = f"• {point}"
            p.font.name = self.FONT_NAME
            p.font.size = Pt(14)
            p.font.color.rgb = self.COLOR_TEXT
            p.space_after = Pt(12)

        # 4. Conclusion / Footer Area
        if "conclusion" in data:
            # Separator Line
            line = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(6.6), Inches(6.0), Inches(0.02)
            )
            line.fill.solid()
            line.fill.fore_color.rgb = self.COLOR_SECONDARY
            
            concl_shape = slide.shapes.add_textbox(Inches(0.5), Inches(6.7), Inches(6.0), Inches(1.0))
            tf = concl_shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = f"CONCLUSIÓN: {data['conclusion']}"
            p.font.name = self.FONT_NAME
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = self.COLOR_PRIMARY

    def _create_one_pager_pdf(self, data: Dict[str, Any]) -> bytes:
        """Crea un One-Pager PDF de una página usando ReportLab."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Colores (ReportLab uses 0-1 range or HexColor)
        NAVY = HexColor('#003366')
        MEDICAL_BLUE = HexColor('#0072CE')
        SOFT_GREY = HexColor('#F0F2F5')
        DARK_GREY = HexColor('#333333')
        
        # 1. Header Background
        c.setFillColor(NAVY)
        c.rect(0, height - 1.5*inch, width, 1.5*inch, fill=1, stroke=0)
        
        # Accent Line
        c.setFillColor(MEDICAL_BLUE)
        c.rect(0, height - 1.6*inch, width, 0.1*inch, fill=1, stroke=0)
        
        # Title
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 24)
        title = data.get("title", "Executive Summary").upper()
        # Simple text wrap for title if too long
        if len(title) > 50:
             c.drawString(0.5*inch, height - 0.7*inch, title[:50] + "...")
        else:
             c.drawString(0.5*inch, height - 0.7*inch, title)
             
        # Subtitle / Main Insight
        c.setFont("Helvetica-Oblique", 14)
        c.setFillColor(MEDICAL_BLUE)
        insight = data.get("main_insight", "")
        # Draw below header
        text_obj = c.beginText(0.5*inch, height - 2.0*inch)
        text_obj.setFont("Helvetica-Oblique", 12)
        text_obj.setFillColor(DARK_GREY)
        
        # Wrap insight text
        import textwrap
        wrapped_insight = textwrap.wrap(insight, width=90)
        for line in wrapped_insight:
            text_obj.textLine(line)
        c.drawText(text_obj)
        
        y_pos_after_insight = height - 2.0*inch - (len(wrapped_insight) * 14) - 0.5*inch

        # 2. Key Stats (3 Circles across the page)
        stats = data.get("key_stats", [])[:3]
        circle_y = y_pos_after_insight - 1.2*inch
        x_positions = [width/4 - 0.5*inch, width/2, 3*width/4 + 0.5*inch]
        
        for i, stat in enumerate(stats):
            x_center = x_positions[i]
            y_center = circle_y
            r = 0.8*inch
            
            # Circle
            c.setFillColor(MEDICAL_BLUE)
            c.circle(x_center, y_center, r, fill=1, stroke=0)
            
            # Value
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 18)
            val = stat.get("value", "")
            val_width = c.stringWidth(val, "Helvetica-Bold", 18)
            c.drawString(x_center - val_width/2, y_center + 5, val)
            
            # Label
            c.setFont("Helvetica", 10)
            lbl = stat.get("label", "")
            # Simple wrap for label
            words = lbl.split()
            if len(words) > 2:
                line1 = " ".join(words[:2])
                line2 = " ".join(words[2:])
                w1 = c.stringWidth(line1, "Helvetica", 10)
                w2 = c.stringWidth(line2, "Helvetica", 10)
                c.drawString(x_center - w1/2, y_center - 15, line1)
                c.drawString(x_center - w2/2, y_center - 27, line2)
            else:
                w1 = c.stringWidth(lbl, "Helvetica", 10)
                c.drawString(x_center - w1/2, y_center - 15, lbl)

        # 3. Key Takeaways
        y_start_takeaways = circle_y - 1.2*inch
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(0.5*inch, y_start_takeaways, "HALLAZGOS CLAVE")
        
        c.setStrokeColor(MEDICAL_BLUE)
        c.line(0.5*inch, y_start_takeaways - 5, 3.0*inch, y_start_takeaways - 5)
        
        y_text = y_start_takeaways - 30
        c.setFont("Helvetica", 11)
        c.setFillColor(DARK_GREY)
        
        for point in data.get("takeaways", []):
            wrapped_point = textwrap.wrap(f"• {point}", width=95)
            for line in wrapped_point:
                c.drawString(0.5*inch, y_text, line)
                y_text -= 16
            y_text -= 8 # Extra space between points

        # 4. Conclusion
        y_conclusion = 1.5*inch
        
        # Background box for conclusion
        c.setFillColor(SOFT_GREY)
        c.roundRect(0.4*inch, 0.4*inch, width - 0.8*inch, 1.2*inch, 10, fill=1, stroke=0)
        
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.6*inch, 1.3*inch, "CONCLUSIÓN:")
        
        c.setFont("Helvetica", 11)
        c.setFillColor(DARK_GREY)
        conclusion = data.get("conclusion", "")
        wrapped_conc = textwrap.wrap(conclusion, width=90)
        y_c = 1.1*inch
        for line in wrapped_conc:
            c.drawString(0.6*inch, y_c, line)
            y_c -= 14
            
        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor('#999999'))
        c.drawRightString(width - 0.5*inch, 0.2*inch, "Inphormed AI • Generado automáticamente")

        c.showPage()
        c.save()
        
        buffer.seek(0)
        return buffer.read()

    def generate_presentation(self, text: str, num_slides: int, image_paths: List[str] = [], style: str = "default") -> bytes:
        # 1. Obtener estructura JSON del LLM
        structure = self._get_presentation_structure(text, num_slides, len(image_paths), style)
        
        if style == "one_pager":
            return self._create_one_pager_pdf(structure)
        
        # 2. Crear PPTX
        prs = Presentation()
        
        if style == "one_pager":
            # Fallback dead code logic just in case, but should be handled above
            self._create_dashboard_slide(prs, structure)
        else:
            # --- Slide 1: Título ---
            title_slide_layout = prs.slide_layouts[6] # Blank
            slide = prs.slides.add_slide(title_slide_layout)
            self._apply_theme(slide, is_title_slide=True)
            
            # Título (Sobre la banda oscura o a la derecha)
            title_text = structure.get("title", "Presentación Ejecutiva")
            
            # Título Principal (Navy sobre Blanco)
            title_shape = slide.shapes.add_textbox(Inches(3.5), Inches(2.5), Inches(6.0), Inches(3.0))
            tf = title_shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = title_text
            p.font.name = self.FONT_NAME
            p.font.size = Pt(40)
            p.font.bold = True
            p.font.color.rgb = self.COLOR_PRIMARY
            p.alignment = PP_ALIGN.LEFT
            
            # Subtítulo
            subtitle_shape = slide.shapes.add_textbox(Inches(3.5), Inches(4.5), Inches(6.0), Inches(1.0))
            tf = subtitle_shape.text_frame
            p = tf.paragraphs[0]
            p.text = "Generado por Inphormed AI"
            p.font.name = self.FONT_NAME
            p.font.size = Pt(18)
            p.font.color.rgb = self.COLOR_SECONDARY

            # --- Slides de Contenido ---
            blank_layout = prs.slide_layouts[6]
            img_index = 0
            
            for slide_data in structure.get("slides", []):
                slide = prs.slides.add_slide(blank_layout)
                self._apply_theme(slide, is_title_slide=False)
                
                # Título de Slide
                title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(0.8))
                tf = title_shape.text_frame
                p = tf.paragraphs[0]
                p.text = slide_data.get("title", "").upper()
                p.font.name = self.FONT_NAME
                p.font.size = Pt(24)
                p.font.bold = True
                p.font.color.rgb = self.COLOR_PRIMARY
                
                layout_type = slide_data.get("layout", "title_body")
                points = slide_data.get("points", [])
                
                # --- Lógica de Layouts ---
                
                if layout_type == "image_right" and image_paths:
                    # Texto Izq (45%), Imagen Der (45%)
                    body_shape = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(4.5), Inches(5.0))
                    tf = body_shape.text_frame
                    tf.word_wrap = True
                    for point in points:
                        p = tf.add_paragraph()
                        p.text = f"• {point}"
                        p.font.name = self.FONT_NAME
                        p.font.size = Pt(18)
                        p.font.color.rgb = self.COLOR_TEXT
                        p.space_after = Pt(14)

                    try:
                        current_img = image_paths[img_index % len(image_paths)]
                        # Imagen con borde sutil
                        pic = slide.shapes.add_picture(current_img, Inches(5.2), Inches(1.5), width=Inches(4.3))
                        
                        # Borde
                        rect = slide.shapes.add_shape(
                            MSO_SHAPE.RECTANGLE, Inches(5.2), Inches(1.5), Inches(4.3), pic.height
                        )
                        rect.fill.background()
                        rect.line.color.rgb = self.COLOR_SECONDARY
                        rect.line.width = Pt(1.0)
                        
                        img_index += 1
                    except Exception as e:
                        print(f"Error imagen: {e}")

                elif layout_type == "two_column":
                    # Dos columnas de texto
                    mid_point = len(points) // 2
                    col1_points = points[:mid_point]
                    col2_points = points[mid_point:]
                    
                    # Col 1
                    body1 = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(4.2), Inches(5.0))
                    tf1 = body1.text_frame
                    tf1.word_wrap = True
                    for point in col1_points:
                        p = tf1.add_paragraph()
                        p.text = f"• {point}"
                        p.font.name = self.FONT_NAME
                        p.font.size = Pt(18)
                        p.font.color.rgb = self.COLOR_TEXT
                        p.space_after = Pt(14)
                    
                    # Col 2
                    body2 = slide.shapes.add_textbox(Inches(5.0), Inches(1.5), Inches(4.5), Inches(5.0))
                    tf2 = body2.text_frame
                    tf2.word_wrap = True
                    for point in col2_points:
                        p = tf2.add_paragraph()
                        p.text = f"• {point}"
                        p.font.name = self.FONT_NAME
                        p.font.size = Pt(18)
                        p.font.color.rgb = self.COLOR_TEXT
                        p.space_after = Pt(14)

                elif layout_type == "big_number":
                    # FIX: Estructura Dato + Etiqueta + Explicación
                    
                    # Asumimos estructura: [DATO_CORTO, ETIQUETA, ...explicación...]
                    raw_data = points[0] if points else "0"
                    # Intentar separar si el LLM falló y puso todo junto (ej: "72 artículos")
                    if len(raw_data) > 5 and " " in raw_data:
                        parts = raw_data.split(" ", 1)
                        big_text = parts[0]
                        label_text = parts[1]
                        desc_text = points[1:]
                    else:
                        big_text = raw_data
                        label_text = points[1] if len(points) > 1 else ""
                        desc_text = points[2:] if len(points) > 2 else []
                    
                    # Columna Izquierda: Círculo con Dato
                    # Círculo
                    oval = slide.shapes.add_shape(
                        MSO_SHAPE.OVAL, Inches(0.8), Inches(2.0), Inches(3.0), Inches(3.0)
                    )
                    oval.fill.solid()
                    oval.fill.fore_color.rgb = self.COLOR_SECONDARY
                    oval.line.fill.background()
                    
                    # Número (Grande, centrado)
                    num_shape = slide.shapes.add_textbox(Inches(0.8), Inches(2.6), Inches(3.0), Inches(1.2))
                    tf = num_shape.text_frame
                    p = tf.paragraphs[0]
                    p.text = big_text
                    p.font.name = self.FONT_NAME
                    p.font.size = Pt(54)
                    p.font.bold = True
                    p.font.color.rgb = self.COLOR_BG
                    p.alignment = PP_ALIGN.CENTER
                    
                    # Etiqueta (Debajo del número, dentro del círculo)
                    label_shape = slide.shapes.add_textbox(Inches(1.0), Inches(3.8), Inches(2.6), Inches(0.8))
                    tf = label_shape.text_frame
                    tf.word_wrap = True
                    p = tf.paragraphs[0]
                    p.text = label_text
                    p.font.name = self.FONT_NAME
                    p.font.size = Pt(16)
                    p.font.bold = True
                    p.font.color.rgb = self.COLOR_BG
                    p.alignment = PP_ALIGN.CENTER
                    
                    # Columna Derecha: Texto Explicativo
                    body = slide.shapes.add_textbox(Inches(4.2), Inches(2.0), Inches(5.3), Inches(4.5))
                    tf = body.text_frame
                    tf.word_wrap = True
                    for point in desc_text:
                        p = tf.add_paragraph()
                        p.text = f"• {point}"
                        p.font.name = self.FONT_NAME
                        p.font.size = Pt(20)
                        p.font.color.rgb = self.COLOR_TEXT
                        p.space_after = Pt(14)

                elif layout_type == "quote":
                    # Cita centrada con fondo gris claro
                    bg_rect = slide.shapes.add_shape(
                        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(2.5), Inches(8.0), Inches(2.5)
                    )
                    bg_rect.fill.solid()
                    bg_rect.fill.fore_color.rgb = self.COLOR_LIGHT_BG
                    bg_rect.line.color.rgb = self.COLOR_SECONDARY
                    
                    body_shape = slide.shapes.add_textbox(Inches(1.5), Inches(3.0), Inches(7.0), Inches(1.5))
                    tf = body_shape.text_frame
                    tf.word_wrap = True
                    p = tf.paragraphs[0]
                    p.text = f'"{points[0]}"' if points else ""
                    p.font.name = self.FONT_NAME
                    p.font.size = Pt(24)
                    p.font.italic = True
                    p.font.color.rgb = self.COLOR_PRIMARY
                    p.alignment = PP_ALIGN.CENTER

                else:
                    # Default: Title and Body
                    body_shape = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5))
                    tf = body_shape.text_frame
                    tf.word_wrap = True
                    for point in points:
                        p = tf.add_paragraph()
                        p.text = f"• {point}"
                        p.font.name = self.FONT_NAME
                        p.font.size = Pt(20)
                        p.font.color.rgb = self.COLOR_TEXT
                        p.space_after = Pt(14)

                # --- Speaker Notes ---
                notes_slide = slide.notes_slide
                text_frame = notes_slide.notes_text_frame
                text_frame.text = slide_data.get("speaker_notes", "")

        # 3. Guardar
        output = io.BytesIO()
        prs.save(output)
        output.seek(0)
        return output.read()

    def _get_presentation_structure(self, text: str, num_slides: int, num_images: int, style: str = "default") -> Dict[str, Any]:
        """
        Usa el LLM para estructurar el contenido.
        """
        if style == "one_pager":
            system_prompt = """
            Eres un consultor estratégico senior en la industria farmacéutica.
            Tu tarea es sintetizar un paper clínico en un "Executive One-Pager" (Dashboard de una sola página).

            INPUT: Texto técnico de un estudio clínico.
            OUTPUT: JSON con la estructura exacta para el dashboard.

            ESTRUCTURA JSON REQUERIDA:
            {
                "title": "Título Corto e Impactante del Estudio",
                "main_insight": "La conclusión o hallazgo más importante en una frase (subtítulo).",
                "key_stats": [
                    {"value": "45%", "label": "Reducción de Riesgo"},
                    {"value": "N=1200", "label": "Pacientes"},
                    {"value": "<0.05", "label": "Valor P"}
                ],
                "takeaways": [
                    "Hallazgo clave 1 (breve)",
                    "Hallazgo clave 2 (breve)",
                    "Hallazgo clave 3 (breve)",
                    "Hallazgo clave 4 (breve)"
                ],
                "conclusion": "Frase final contundente sobre la implicación clínica."
            }
            
            REGLAS:
            - Sé extremadamente conciso.
            - "key_stats": Extrae 3 métricas numéricas clave. "value" debe ser corto (ej: "45%").
            - "takeaways": Máximo 5 puntos.
            """
        else:
            system_prompt = f"""
            Eres un diseñador de presentaciones profesional para la industria FARMACÉUTICA.
            
            INPUT: Texto técnico y {num_images} imágenes disponibles extraídas del documento.
            OUTPUT: JSON para una presentación de {num_slides} diapositivas.
            
            LAYOUTS DISPONIBLES:
            - "title_body": Lista de puntos estándar.
            - "two_column": Dos columnas de texto (para comparaciones o listas largas).
            - "image_right": Texto a la izquierda, IMAGEN a la derecha. (¡USA ESTO SI HAY IMÁGENES!)
            - "big_number": Estadística destacada. Estructura estricta: [DATO_CORTO, ETIQUETA, ...explicación].
            - "quote": Una cita o frase impactante centrada.
            
            REGLAS CRÍTICAS:
            1.  **USO DE IMÁGENES**: Tienes {num_images} imágenes disponibles. DEBES usar el layout "image_right" en al menos {min(num_images, num_slides // 2)} diapositivas para mostrar gráficos/tablas.
            2.  **DATOS (big_number)**: 
                - Punto 1: SOLO EL NÚMERO (ej: "45%", "120"). Máx 5 caracteres.
                - Punto 2: La etiqueta corta (ej: "Pacientes", "Crecimiento").
                - Punto 3+: Explicación detallada.
            3.  **VARIEDAD**: No uses "title_body" en todas. Mezcla layouts.
            4.  **CONTENIDO**: Sintetiza. No pegues párrafos.
            
            Formato JSON:
            {{
              "title": "Título",
              "slides": [
                {{
                  "title": "...",
                  "layout": "image_right", 
                  "points": ["..."],
                  "speaker_notes": "..."
                }}
              ]
            }}
            """
        
        max_chars = 15000
        truncated_text = text[:max_chars] + "..." if len(text) > max_chars else text
        user_prompt = f"Genera la estructura:\n\n{truncated_text}"
        
        data = self.llm.chat_with_json(system_prompt, user_prompt)
        
        if not data:
             return {
                 "title": "Error",
                 "slides": [{"title": "Error", "points": ["Fallo al generar."], "layout": "title_body"}]
             }
             
        return data
