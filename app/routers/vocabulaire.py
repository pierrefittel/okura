from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import vocabulaire as schemas
from app.crud import vocabulaire as crud
from app.services.nlp import analyze_japanese_text 

router = APIRouter(prefix="/lists", tags=["Listes"])

@router.post("/", response_model=schemas.VocabListResponse)
def create_list(item: schemas.VocabListCreate, db: Session = Depends(get_db)):
    return crud.create_list(db, item)

@router.get("/", response_model=List[schemas.VocabListResponse])
def get_lists(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return crud.get_lists(db, skip, limit)

@router.get("/{list_id}", response_model=schemas.VocabListWithCards)
def get_list_details(list_id: int, db: Session = Depends(get_db)):
    db_list = crud.get_list_with_cards(db, list_id)
    if not db_list:
        raise HTTPException(status_code=404, detail="Liste introuvable")
    return db_list

@router.post("/{list_id}/cards", response_model=schemas.VocabCardResponse)
def add_card(list_id: int, item: schemas.VocabCardCreate, db: Session = Depends(get_db)):
    if not crud.get_list_with_cards(db, list_id):
        raise HTTPException(status_code=404, detail="Liste introuvable")
    try:
        return crud.add_card_to_list(db, list_id, item)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Erreur lors de l'ajout (Doublon probable).")

# --- NOUVELLE ROUTE ---
@router.post("/{list_id}/cards/bulk", response_model=List[schemas.VocabCardResponse])
def add_cards_bulk(list_id: int, items: List[schemas.VocabCardCreate], db: Session = Depends(get_db)):
    """
    Importe une liste de mots.
    Ignore automatiquement les mots déjà présents dans la liste (basé sur ent_seq).
    """
    # 1. Vérif liste existe
    if not crud.get_list_with_cards(db, list_id):
        raise HTTPException(status_code=404, detail="Liste introuvable")
    
    # 2. Appel du CRUD intelligent
    return crud.add_cards_to_list_bulk(db, list_id, items)

@router.post("/analyze", response_model=schemas.AnalyzeResponse, tags=["Outils"])
def analyze_text(request: schemas.AnalyzeRequest):
    return {"candidates": analyze_japanese_text(request.text)}