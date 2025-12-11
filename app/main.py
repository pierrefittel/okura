from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # <--- Nouveau
from fastapi.responses import RedirectResponse
from app.core.database import engine, Base
from app.routers import vocabulaire

# Création des tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Projet Okura")

# Enregistrement du router API
app.include_router(vocabulaire.router)

# --- NOUVEAU : Servir le Frontend ---
# On monte le dossier "static" sur l'URL /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Redirection automatique de la racine (/) vers notre interface (/static/index.html)
@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")