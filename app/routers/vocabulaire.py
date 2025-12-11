from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import vocabulaire as schemas
from app.crud import vocabulaire as crud
from app.services.nlp import analyze_japanese_text 

router = APIRouter(prefix="/lists", tags=["Listes"])

@router.get("/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    return crud.get_dashboard_stats(db)

# --- SRS ROUTES ---
@router.get("/training/due", response_model=List[schemas.VocabCardResponse])
def get_due_cards(limit: int = 50, list_id: Optional[int] = None, db: Session = Depends(get_db)):
    return crud.get_due_cards(db, limit, list_id)

@router.post("/cards/{card_id}/review", response_model=schemas.VocabCardResponse)
def review_card(card_id: int, review: schemas.ReviewAttempt, db: Session = Depends(get_db)):
    card = crud.process_review(db, card_id, review.quality)
    if not card: raise HTTPException(404, "Not found")
    return card

# --- ROUTES STANDARD ---
@router.post("/", response_model=schemas.VocabListResponse)
def create_list(item: schemas.VocabListCreate, db: Session = Depends(get_db)):
    return crud.create_list(db, item)

@router.get("/", response_model=List[schemas.VocabListResponse])
def get_lists(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return crud.get_lists(db, skip, limit)

@router.get("/{list_id}", response_model=schemas.VocabListWithCards)
def get_list_details(list_id: int, db: Session = Depends(get_db)):
    db_list = crud.get_list_with_cards(db, list_id)
    if not db_list: raise HTTPException(404, "Not found")
    return db_list

@router.post("/{list_id}/cards", response_model=schemas.VocabCardResponse)
def add_card(list_id: int, item: schemas.VocabCardCreate, db: Session = Depends(get_db)):
    if not crud.get_list_with_cards(db, list_id): raise HTTPException(404, "Not found")
    return crud.add_card_to_list(db, list_id, item)

@router.post("/{list_id}/cards/bulk", response_model=List[schemas.VocabCardResponse])
def add_cards_bulk(list_id: int, items: List[schemas.VocabCardCreate], db: Session = Depends(get_db)):
    if not crud.get_list_with_cards(db, list_id): raise HTTPException(404, "Not found")
    return crud.add_cards_to_list_bulk(db, list_id, items)

@router.delete("/cards/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    if not crud.delete_card(db, card_id): raise HTTPException(404, "Not found")
    return {"ok": True}

@router.post("/analyze", response_model=schemas.AnalyzeResponse)
def analyze_text(request: schemas.AnalyzeRequest):
    return analyze_japanese_text(request.text)

# --- DATA ---
@router.get("/data/export")
def export_data(db: Session = Depends(get_db)):
    csv_content = crud.export_to_csv(db)
    return Response(
        content=csv_content, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=okura_backup.csv"}
    )

@router.post("/data/import")
async def import_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'): 
        raise HTTPException(400, "Fichier CSV requis")
    
    content = await file.read()
    stats = crud.import_from_csv(db, content.decode('utf-8'))
    return {"message": "Import terminé", "details": stats}