# Guía de Inicio Rápido - Inphormed

Este documento explica cómo arrancar los servidores (Backend, Frontend y Base de Datos) de forma autónoma.

## Opción 1: Docker (Recomendada)

Esta es la forma más sencilla, ya que levanta todo (Backend, Frontend y Base de Datos) con un solo comando.

### Pasos:
1. Abre una terminal en la carpeta raíz del proyecto (`inphormed`).
2. Ejecuta el siguiente comando:
   ```bash
   docker-compose up
   ```
   *Si has hecho cambios en las dependencias (nuevas librerías en python o npm), usa:*
   ```bash
   docker-compose up --build
   ```

3. Espera a que los logs indiquen que los servicios están listos.
   - **Frontend:** Accesible en [http://localhost:3000](http://localhost:3000)
   - **Backend:** Accesible en [http://localhost:8000](http://localhost:8000)
   - **Documentación API:** [http://localhost:8000/docs](http://localhost:8000/docs)

4. Para detener todo, presiona `Ctrl + C` en la terminal.

---

## Opción 2: Ejecución Manual (Desarrollo Local)

Si prefieres ejecutar cada parte por separado (útil si estás depurando solo una parte).

### 1. Base de Datos (Qdrant)
Necesitas tener Qdrant corriendo. Lo más fácil es usar Docker solo para esto:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 2. Backend (Python/FastAPI)
1. Abre una terminal en la raíz (`inphormed`).
2. Activa tu entorno virtual (si usas uno):
   ```bash
   .\venv\Scripts\activate
   ```
3. Asegúrate de tener las variables de entorno configuradas (archivo `.env`).
4. Ejecuta el servidor:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### 3. Frontend (Next.js)
1. Abre una **nueva** terminal.
2. Navega a la carpeta `frontend`:
   ```bash
   cd frontend
   ```
3. Instala dependencias (solo la primera vez):
   ```bash
   npm install
   ```
4. Arranca el servidor de desarrollo:
   ```bash
   npm run dev
   ```
5. Abre [http://localhost:3000](http://localhost:3000) en tu navegador.
