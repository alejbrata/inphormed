# 🧠 Inphormed

**Inphormed** es una plataforma de **agentes de IA generativa** especializada en **marketing farmacéutico y validación de claims científicos**, desarrollada como parte del **Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa (EBIS, 2024-2025)**.

## 🚀 Objetivo

Automatizar la revisión, generación y validación de materiales médicos y promocionales mediante agentes de IA, buscando **precisión, cumplimiento regulatorio (EMA/FDA)** y trazabilidad.

## ✨ Funcionalidades

- **Validación de claims** (enfoque *LLM-first*): extrae los claims de un texto o de una presentación PPTX y los contrasta con evidencia de **PubMed**, accediendo al texto completo de los artículos de PMC con un crawler (Playwright).
- **Generación de materiales** a partir de un PDF o un texto: resumen ejecutivo, presentación PPTX o one-pager en PDF, *battle card* de competidor, carta de respuesta estándar (MedInfo) y podcast (guion + audio).
- **Chat copiloto** integrado en el frontend.

## 🏗️ Arquitectura

- **Backend:** FastAPI (Python)
- **Frontend:** Next.js + React + Tailwind
- **LLM:** OpenAI (por defecto), Azure OpenAI o Gemini, seleccionable con `LLM_PROVIDER`
- **Audio:** OpenAI TTS
- **Documentos:** python-pptx, python-docx y WeasyPrint
- **Infraestructura:** Docker Compose (API, frontend y Qdrant)

## 🧪 En desarrollo

El repositorio incluye módulos que todavía **no están conectados a la API**:

- Búsqueda híbrida: vectorial con Qdrant + léxica BM25 con Whoosh, y embeddings con `sentence-transformers`.
- Conectores a Europe PMC, Crossref, ClinicalTrials.gov y EMA.

## ⚙️ Instalación rápida

```bash
git clone https://github.com/alejbrata/inphormed.git
cd inphormed
cp .env.example .env        # y rellena tus claves
docker-compose up --build
```

- Frontend: http://localhost:3000
- API y documentación: http://localhost:8000/docs

Para ejecutar cada parte por separado, consulta [INSTRUCCIONES_INICIO.md](INSTRUCCIONES_INICIO.md).

## 📄 Plantilla de presentaciones

La generación de presentaciones PPTX usa una plantilla que **no se incluye en el repositorio**. Coloca tu propia plantilla en la raíz del proyecto con el nombre `Innovacion-en-Salud-Un-Enfoque-Farmaceutico.pptx`, o cambia la ruta en `app/agents/generation_agent.py`. El one-pager en PDF no la necesita: usa la plantilla HTML de `app/templates/`.

## 📜 Licencia

Copyright (C) 2025 Alejandro Bravo

Este proyecto se distribuye bajo la licencia **GNU Affero General Public License v3.0** (AGPL-3.0). Consulta el fichero [LICENSE](LICENSE).

Se usa AGPL-3.0 porque el proyecto depende de [PyMuPDF](https://github.com/pymupdf/PyMuPDF), que se distribuye bajo esa misma licencia. Puedes usar, modificar y redistribuir el código, siempre que publiques tus cambios bajo la misma licencia, también si ofreces la aplicación como servicio a través de una red.
