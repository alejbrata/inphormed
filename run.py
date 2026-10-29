# run.py
import asyncio
import sys
import uvicorn
import os

def main():
    # FUERZA EL USO DE PROACTOR EN WINDOWS
    # Esto es obligatorio para que Playwright funcione dentro de Uvicorn/FastAPI
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("✅ Política de Event Loop configurada a WindowsProactor (Soporte para Navegador)")

    # Configuración del servidor
    # Equivalente a: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()