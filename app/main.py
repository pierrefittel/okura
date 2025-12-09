from fastapi import FastAPI
from app.core.database import engine, Base
from app.routers import vocabulaire # <-- Import du router

# Création des tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Projet Okura")

# Enregistrement du router
app.include_router(vocabulaire.router) # <-- Activation

@app.get("/")
def read_root():
    return {"message": "Bienvenue dans l'entrepôt Okura"}