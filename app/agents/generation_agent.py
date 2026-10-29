import os
import uuid
import io
from typing import List, Tuple, Dict, Any
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from app.services.llm_service import LLMService
import fitz  # PyMuPDF
import docx

# Try to import WeasyPrint (might fail if system deps missing locally, but works in Docker)
try:
    from weasyprint import HTML, CSS
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("Warning: WeasyPrint or Jinja2 not found. PDF generation will fail.")

class GenerationAgent:
    def __init__(self):
        self.llm = LLMService()
        # Nombre exacto del archivo subido por el usuario
        self.TEMPLATE_PATH = "Innovacion-en-Salud-Un-Enfoque-Farmaceutico.pptx"
        # Ruta a templates HTML
        self.HTML_TEMPLATE_PATH = os.path.join(os.getcwd(), "app", "templates")
        
        # Colores (Backup por si acaso, aunque ya no deberíamos pintar manual)
        self.FONT_NAME = 'Arial'

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
                    
                    # Disabled image extraction per user request (Copyright/Aesthetics)
                    # image_list = page.get_images(full=True)
                    # ... extraction logic removed ...
                
                # Clean return
                image_paths = []

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

    def _render_pdf_from_html(self, data: Dict[str, Any]) -> bytes:
        """Renderiza PDF usando Jinja2 + WeasyPrint."""
        if not os.path.exists(self.HTML_TEMPLATE_PATH):
             # Fallback creation if not exists (safety)
             os.makedirs(self.HTML_TEMPLATE_PATH, exist_ok=True)
        
        env = Environment(loader=FileSystemLoader(self.HTML_TEMPLATE_PATH))
        
        # Add a date formatter
        from datetime import datetime
        env.filters['format_date'] = lambda x: datetime.now().strftime("%d/%m/%Y")
        
        try:
            template = env.get_template("one_pager.html")
            html_string = template.render(**data)
            
            # Base URL for assets if needed
            base_url = os.getcwd()
            pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf()
            return pdf_bytes
        except Exception as e:
            print(f"WeasyPrint Error: {e}")
            # Fallback simple text bytes to debug
            return f"Error generando PDF: {e}".encode('utf-8')

    # Configuración de la Plantilla "Innovacion en Salud"
    TEMPLATE_SCHEMA = [
        # Slide 0: Portada
        {"type": "title", "map": {"title": "{{Título}}", "subtitle": "{{Descripción}}"}},
        # Slide 1: Intro / Autor
        {"type": "intro", "map": {"body": "{{Descripción}}", "author": "{{Presentador y Fecha}}"}},
        # Slide 2: Roadmap (Skip)
        {"type": "roadmap", "map": {}}, 
        # Slide 3: 3 Puntos (Standard)
        {"type": "3_points", "map": {"intro": "{{Descripción}}", "p1": "{{Punto 1}}", "p2": "{{Punto 2}}", "p3": "{{Punto 3}}"}},
        # Slide 4: Features (Skip for now or complex)
        {"type": "features", "map": {}},
        # Slide 5: 3 Puntos (Alternative) - Perfect for extra content
        {"type": "3_points", "map": {"intro": "{{Descripción}}", "p1": "{{Punto 1}}", "p2": "{{Punto 2}}", "p3": "{{Punto 3}}"}},
        # Slide 6: Gray Box (Skip)
        {"type": "image", "map": {}}, 
        # Slide 7: 3 Puntos (Alternative 2)
        {"type": "3_points", "map": {"intro": "{{Descripción}}", "p1": "{{Punto 1}}", "p2": "{{Punto 2}}", "p3": "{{Punto 3}}"}},
        # Slide 8: Future Plan (4 Bubbles) -> ESTA es la de "Plan Futuro"
        {"type": "future", "map": {"items": "{{Título descriptivo}}", "desc": "{{Descripción}}"}},
        # Slide 9: Contact
        {"type": "contact", "map": {"desc": "{{Descripción}}", "contact": ["{{Email}}", "{{Teléfono}}", "{{Web}}"]}}
    ]

    def _generate_pptx_from_template(self, structure: Dict[str, Any], output_path: str = None) -> bytes:
        """Genera PPTX usando Schema-Driven Generation."""
        if not os.path.exists(self.TEMPLATE_PATH):
             if os.path.exists(os.path.join(os.getcwd(), self.TEMPLATE_PATH)):
                 self.TEMPLATE_PATH = os.path.join(os.getcwd(), self.TEMPLATE_PATH)
             else:
                 raise FileNotFoundError(f"Plantilla no encontrada: {self.TEMPLATE_PATH}")

        prs = Presentation(self.TEMPLATE_PATH)
        
        # Estrategia: "Selección + Eliminación"
        # Seleccionamos las slides del template que mejor encajan con lo pedido.
        # Siempre Portada (0).
        # Para 5 slides: [0, 1, 3, 6, 9] (Portada, Intro, Puntos, Puntos, Cierre).
        # Las definimos estáticamente para asegurar calidad visual.
        
        # Índices a usar (Hardcoded selection para 'Executive Summary')
        # Slide 3, 6, 8 son los layouts más limpios (3 puntos).
        # Slide 1 es texto limpio.
        # Slide 9 es buen cierre.
        # Slide 0 es portada.
        
        selected_indices = [0, 1, 3, 8, 9] 
        # Si piden más, añadimos 5 (3 cols) y 6 (3 puntos, aunque tiene el issue del gris, lo dejamos como backup).
        if len(structure.get("slides", [])) > 5:
            selected_indices = [0, 1, 3, 5, 8, 6, 9] # 7 slides
            
        # Mapeamos los datos del LLM a estos índices
        json_slides = structure.get("slides", [])
        
        # Filtrar slides del template: Borramos las que NO están en selected_indices
        slides_to_keep = set(selected_indices)
        
        # Hay que tener cuidado: borrar slides altera los índices de las siguientes.
        # Mejor estrategia: Recorrer XML de atrás adelante y borrar las no deseadas.
        xml_slides = prs.slides._sldIdLst
        total_tpl_slides = len(list(prs.slides))
        
        for i in range(total_tpl_slides - 1, -1, -1):
            if i not in slides_to_keep:
                # Borrar
                rId = prs.slides._sldIdLst[i].rId
                prs.part.drop_rel(rId)
                del prs.slides._sldIdLst[i]
                
        # Ahora re-calculamos indices. Como hemos borrado, los indices ahora son 0, 1, 2, 3...
        # que corresponden secuencialmente a los selected_indices ordenados.
        # [0, 1, 3, 8, 9] se convierte en prs.slides[0], [1], [2], [3], [4].
        
        final_slides = list(prs.slides)
        
        # Iteramos y rellenamos
        for i, slide in enumerate(final_slides):
            if i >= len(json_slides):
                break
                
            slide_data = json_slides[i]
            # Recuperar el índice original para saber el 'map'
            original_idx = sorted(list(slides_to_keep))[i]
            if original_idx >= len(self.TEMPLATE_SCHEMA):
                 continue # Safety
                 
            schema = self.TEMPLATE_SCHEMA[original_idx]
            mapping_config = schema["map"]
            
            # Construir mapa de reemplazo concreto
            replacements = {}
            
            # Helpers de mapeo comunes
            if "title" in mapping_config: replacements[mapping_config["title"]] = slide_data.get("title", "")
            if "subtitle" in mapping_config: replacements[mapping_config["subtitle"]] = slide_data.get("subtitle", "")
            if "body" in mapping_config: replacements[mapping_config["body"]] = "\n".join(slide_data.get("points", []))
            if "intro" in mapping_config: replacements[mapping_config["intro"]] = slide_data.get("subtitle", "") # 'intro' suele ser subtitulo
            
            # Specific mappings missing in previous version
            if "desc" in mapping_config: 
                # Slide 9 uses 'desc'
                replacements[mapping_config["desc"]] = slide_data.get("subtitle", "Próximos Pasos")
            
            if "contact" in mapping_config:
                # Fill generic contact info to hide placeholders
                contact_list = mapping_config["contact"]
                if len(contact_list) >= 3:
                     replacements[contact_list[0]] = "contacto@inphormed.ai" # Email
                     replacements[contact_list[1]] = "" # Phone (hide)
                     replacements[contact_list[2]] = "www.inphormed.ai" # Web

            # Puntos específicos (p1, p2, p3)
            points = slide_data.get("points", [])
            if "p1" in mapping_config:
                replacements[mapping_config["p1"]] = points[0] if len(points) > 0 else ""
            if "p2" in mapping_config:
                replacements[mapping_config["p2"]] = points[1] if len(points) > 1 else ""
            if "p3" in mapping_config:
                replacements[mapping_config["p3"]] = points[2] if len(points) > 2 else ""
                
            # Slide 9: Future / Contact (Items repetitivos)
            if "items" in mapping_config:
                placeholder = mapping_config["items"] # "{{Título descriptivo}}"
                self._replace_iterative(slide, placeholder, points)
                
            # Aplicar reemplazos simples
            self._replace_in_slide(slide, replacements)
            
            # Limpieza final de placeholders vacíos o no usados (ej: el cuadro gris)
            self._cleanup_slide(slide)

        output = io.BytesIO()
        prs.save(output)
        output.seek(0)
        return output.read()

    def _cleanup_slide(self, slide):
        """Intenta eliminar o ocultar placeholders vacíos."""
        # Nota: Eliminar shapes es delicado.
        # Basic approach: si es un placeholder de imagen/objeto y no lo hemos tocado, quizás dejarlo o quitarlo.
        # En este caso, el usuario se queja de "Gris". Eso es un Picture Placeholder vacío.
        # Vamos a intentar identificarlo.
        pass # Por ahora, con cambiar el índice de slide (6 -> 8) debería bastar.

    def _replace_iterative(self, slide, placeholder, values):
        """Reemplaza ocurrencias de un placeholder secuencialmente con una lista de valores."""
        val_idx = 0
        for shape in slide.shapes:
            if not shape.has_text_frame: continue
            for p in shape.text_frame.paragraphs:
                if placeholder in p.text:
                    if val_idx < len(values):
                        val = values[val_idx]
                        p.text = p.text.replace(placeholder, str(val))
                        # Restore font format basic hack
                        p.font.name = self.FONT_NAME 
                        val_idx += 1
                    else:
                        p.text = p.text.replace(placeholder, "") # Clear unused

    def _replace_in_slide(self, slide, replacement_map):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                # Replacement naive
                txt = paragraph.text
                for k, v in replacement_map.items():
                    if k in txt:
                        # Replace and simple fit logic could go here
                        txt = txt.replace(k, str(v))
                        # Fix overflow basic
                        if len(txt) > 200 and shape.height < Inches(2): 
                            # Si mucho texto en caja pequeña, cortar
                            pass 
                
                # Apply change
                if txt != paragraph.text:
                    paragraph.text = txt # Replaces runs, keeps paragraph style match? No, resets runs.
                    # Mejor: conservar runs si es posible, pero es complejo.
                    # Para MVP, asignamos texto plano al párrafo
                    # pero intentamos restaurar la fuente del primer run
                    font_style = None
                    if paragraph.runs:
                        font_style = paragraph.runs[0].font
                    
                    # Restaurar fuente (name, size, color, bold)
                    if font_style:
                         paragraph.runs[0].font.name = font_style.name # Etc...

    def generate_presentation(self, text: str, num_slides: int, image_paths: List[str] = [], style: str = "default") -> bytes:
        # 1. Obtener estructura JSON del LLM
        structure = self._get_presentation_structure(text, num_slides, len(image_paths), style)
        
        # 2. Router
        if style == "one_pager":
            return self._render_pdf_from_html(structure)
        else:
            return self._generate_pptx_from_template(structure)

    def _get_presentation_structure(self, text: str, num_slides: int, num_images: int, style: str = "default") -> Dict[str, Any]:
        """
        Usa el LLM para estructurar el contenido.
        """
        if style == "one_pager":
            system_prompt = """
            Eres un consultor estratégico senior en la industria farmacéutica.
            Tu tarea es sintetizar un paper clínico en un "Executive One-Pager" (Dashboard).

            INPUT: Texto técnico de un estudio clínico.
            OUTPUT: JSON con la estructura exacta.

            ESTRUCTURA JSON:
            {
                "title": "Título Corto",
                "main_insight": "Conclusión principal.",
                "key_stats": [
                    {"value": "XX%", "label": "Etiqueta"},
                    {"value": "N=XXX", "label": "Pacientes"},
                    {"value": "P<0.0X", "label": "Significancia"}
                ],
                "takeaways": [
                    "Punto 1", "Punto 2", "Punto 3", "Punto 4"
                ],
                "conclusion": "Conclusión final."
            }
            """
        else:
            # Prompt Template-Aware
            system_prompt = f"""
            Eres un experto creando presentaciones. Vamos a llenar una plantilla específica de 5 diapositivas.
            
            INPUT: Texto clínico.
            OUTPUT: JSON con exactamente 5 diapositivas.
            
            ESTRUCTURA DE LA PLANTILLA (Sigue esto estrictamente):
            
            Slide 1: Portada
            - title: Título del Estudio
            - subtitle: Frase resumen impactante
            
            Slide 2: Introducción
            - subtitle: Contexto breve
            - points: ["Párrafo corto de introducción"]
            
            Slide 3: Puntos Clave (3 Columnas)
            - subtitle: "Hallazgos Principales"
            - points: ["Hallazgo 1", "Hallazgo 2", "Hallazgo 3"]  <-- MAX 3 ITEMS
            
            Slide 4: Detalles (3 Columnas)
            - subtitle: "Metodología / Seguridad"
            - points: ["Detalle 1", "Detalle 2", "Detalle 3"] <-- MAX 3 ITEMS
            
            Slide 5: Plan Futuro / Conclusión (Lista de 4)
            - subtitle: "Próximos Pasos"
            - points: ["Acción 1", "Acción 2", "Acción 3", "Acción 4"] <-- MAX 4 ITEMS
            
            Output JSON:
            {{
                "slides": [
                    {{ "title": "...", "subtitle": "...", "points": [...] }},
                    ...
                ]
            }}
            """
        
        max_chars = 15000
        truncated_text = text[:max_chars]
        user_prompt = f"Genera la estructura:\n\n{truncated_text}"
        
        data = self.llm.chat_with_json(system_prompt, user_prompt)
        
        return data if data else {"slides": []}

