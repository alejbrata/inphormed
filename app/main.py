from fastapi import FastAPI

app = FastAPI(title="Inphormed API")

@app.get("/")
def root():
    return {"message": "Inphormed backend en funcionamiento 🚀"}
