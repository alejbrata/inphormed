from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, StreamingResponse
from app.services.podcast_service import PodcastService
import io
import base64

router = APIRouter(prefix="/api/generate", tags=["generation"])

@router.post("/podcast", summary="Genera un podcast (Audio+Script) desde un PDF")
async def generate_podcast(
    file: UploadFile = File(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF.")

    try:
        # 1. Leer PDF
        content = await file.read()
        service = PodcastService()
        text = service.extract_text_from_pdf(content)

        if not text:
             raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF.")

        # 2. Generar Guion
        script = service.generate_script(text)

        # 3. Generar Audio
        audio_bytes = await service.generate_audio(script)

        # 4. Retornar respuesta compuesta (JSON con script + Audio en base64)
        #    Para simplificar en frontend, enviamos todo en un JSON.
        #    Si el audio fuera muy largo, sería mejor StreamingResponse, 
        #    pero para 3-5 mins (aprox 2-4MB) base64 es manejable.
        
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return JSONResponse({
            "script": script,
            "audio_base64": audio_b64,
            "file_name": file.filename
        })

    except Exception as e:
        print(f"Error generando podcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summary", summary="Genera un resumen ejecutivo desde un PDF")
async def generate_summary(
    file: UploadFile = File(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF.")

    try:
        content = await file.read()
        service = PodcastService()
        text = service.extract_text_from_pdf(content)

        if not text:
             raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF.")

        summary = service.generate_summary(text)
        
        # Generar audio del resumen
        audio_bytes = await service.generate_audio_from_text(summary)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return JSONResponse({
            "summary": summary,
            "audio_base64": audio_b64,
            "file_name": file.filename
        })

    except Exception as e:
        print(f"Error generando resumen: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slides", summary="Genera una presentación PPTX desde texto o archivo")
async def generate_slides(
    background_tasks: BackgroundTasks,
    text: str = Form(None),
    file: UploadFile = File(None),
    num_slides: int = Form(5)
):
    if not text and not file:
        raise HTTPException(status_code=400, detail="Se requiere texto o un archivo.")

    import os
    import shutil

    # Helper para cleanup
    def cleanup_images(image_paths):
        for path in image_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Error borrando imagen temporal {path}: {e}")

    try:
        from app.agents.generation_agent import GenerationAgent
        agent = GenerationAgent()
        
        content_text = ""
        image_paths = []

        if file:
            content = await file.read()
            # Ahora devuelve tupla (texto, imagenes)
            content_text, image_paths = agent.extract_text_from_file(content, file.filename)
        else:
            content_text = text

        if not content_text or len(content_text.strip()) < 50:
             raise HTTPException(status_code=400, detail="El contenido es demasiado corto para generar una presentación.")

        # Generar PPTX pasando imágenes
        pptx_bytes = agent.generate_presentation(content_text, num_slides, image_paths)

        # Programar limpieza
        if image_paths:
            background_tasks.add_task(cleanup_images, image_paths)

        # Retornar como archivo descargable
        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": "attachment; filename=generated_presentation.pptx"}
        )

    except Exception as e:
        print(f"Error generando slides: {e}")
        raise HTTPException(status_code=500, detail=str(e))
