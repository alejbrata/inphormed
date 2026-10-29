# Usamos la imagen oficial de Playwright (que ya trae Python y navegadores)
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /code

# Copiar dependencias
COPY requirements.txt .

# Instalar dependencias del sistema para WeasyPrint y otras herramientas
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY . .

# Exponer puerto
EXPOSE 8000

# Comando de arranque (¡Aquí SÍ podemos usar uvicorn normal!)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]