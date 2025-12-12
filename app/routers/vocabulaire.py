from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import vocabulaire as schemas
from app.crud import vocabulaire as crud
from app.services import nlp 

router = APIRouter(prefix="/lists", tags=["Listes"])

# --- ANALYSE FICHIER ---
@router.post("/analyze/file", response_model=schemas.AnalyzeResponse)
async def analyze_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename.lower()
        text = ""
        if filename.endswith('.epub'):
            text = nlp.extract_text_from_epub(content)
        elif filename.endswith('.html') or filename.endswith('.htm'):
            try: decoded = content.decode('utf-8')
            except: decoded = content.decode('shift_jis', errors='ignore')
            text = nlp.clean_html_text(decoded)
        else:
            try: decoded = content.decode('utf-8')
            except: decoded = content.decode('shift_jis', errors='ignore')
            text = nlp.clean_raw_text(decoded)
            
        if not text.strip(): raise HTTPException(400, "Fichier vide")
        
        return nlp.analyze_text(text, lang="jp") 
        
    except Exception as e:
        raise HTTPException(400, f"Erreur traitement: {str(e)}")

@router.post("/analyze", response_model=schemas.AnalyzeResponse)
def analyze_text(request: schemas.AnalyzeRequest):
    return nlp.analyze_text(request.text, lang=request.lang)

@router.get("/data/export")
def export_data(db: Session = Depends(get_db)):
    return Response(content=crud.export_to_csv(db), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=okura_backup.csv"})

@router.post("/data/import")
async def import_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    return {"message": "Import terminé", "details": crud.import_from_csv(db, content.decode('utf-8'))}

@router.get("/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard(db: Session = Depends(get_db)): return crud.get_dashboard_stats(db)

@router.get("/training/due", response_model=List[schemas.VocabCardResponse])
def get_due_cards(limit: int = 50, list_id: Optional[int] = None, db: Session = Depends(get_db)):
    return crud.get_due_cards(db, limit, list_id)

@router.post("/cards/{card_id}/review", response_model=schemas.VocabCardResponse)
def review_card(card_id: int, review: schemas.ReviewAttempt, db: Session = Depends(get_db)):
    return crud.process_review(db, card_id, review.quality)

@router.post("/", response_model=schemas.VocabListResponse)
def create_list(item: schemas.VocabListCreate, db: Session = Depends(get_db)):
    return crud.create_list(db, item)

@router.get("/", response_model=List[schemas.VocabListResponse])
def get_lists(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return crud.get_lists(db, skip, limit)

@router.get("/{list_id}", response_model=schemas.VocabListWithCards)
def get_list_details(list_id: int, db: Session = Depends(get_db)):
    return crud.get_list_with_cards(db, list_id)

@router.delete("/{list_id}")
def delete_list(list_id: int, db: Session = Depends(get_db)):
    if not crud.delete_list(db, list_id): raise HTTPException(404, "Not found")
    return {"ok": True}

@router.post("/{list_id}/cards", response_model=schemas.VocabCardResponse)
def add_card(list_id: int, item: schemas.VocabCardCreate, db: Session = Depends(get_db)):
    return crud.add_card_to_list(db, list_id, item)

@router.post("/{list_id}/cards/bulk", response_model=List[schemas.VocabCardResponse])
def add_cards_bulk(list_id: int, items: List[schemas.VocabCardCreate], db: Session = Depends(get_db)):
    return crud.add_cards_to_list_bulk(db, list_id, items)

@router.delete("/cards/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    return {"ok": crud.delete_card(db, card_id)}