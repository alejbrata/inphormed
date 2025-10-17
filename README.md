# 🧠 Inphormed

**Inphormed** es una plataforma de **agentes de IA generativa** especializada en **marketing farmacéutico y validación de claims científicos**, desarrollada como parte del **Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa (EBIS, 2024-2025)**.

## 🚀 Objetivo

Automatizar la revisión, generación y validación de materiales médicos y promocionales mediante agentes de IA multimodal y RAG avanzado, garantizando **precisión, cumplimiento regulatorio (EMA/FDA)** y trazabilidad completa.

## 🏗️ Arquitectura (Fase MVP)

- **Backend:** FastAPI + Python 3.11  
- **Vector DB:** Qdrant (local o cloud)  
- **RAG:** LangChain / LlamaIndex  
- **LLM:** GPT-4o / Mistral / Azure OpenAI  
- **ASR / TTS:** Whisper + ElevenLabs  
- **Infraestructura:** Docker + desarrollo local (fase 1) → Azure (fase 2)  

## ⚙️ Instalación rápida

```bash
git clone https://github.com/alejbrata/inphormed.git
cd inphormed
python -m venv venv
source venv/bin/activate   # (o .\venv\Scripts\activate en Windows)
pip install -r requirements.txt
uvicorn app.main:app --reload
