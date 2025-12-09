from fastapi import FastAPI
from app.core.database import engine, Base
from app.models import vocabulaire # Import nécessaire pour que SQLAlchemy voie les tables

# Création des tables dans la base de données (équivalent sommaire de "migrate")
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Projet Okura")

@app.get("/")
def read_root():
    return {"message": "Bienvenue dans l'entrepôt Okura"}