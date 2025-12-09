from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import vocabulaire as schemas
from app.crud import vocabulaire as crud

router = APIRouter(
    prefix="/vocabulaire",
    tags=["vocabulaire"]
)

@router.post("/", response_model=schemas.VocabulaireResponse)
def create_vocab(item: schemas.VocabulaireCreate, db: Session = Depends(get_db)):
    return crud.create_vocabulaire(db=db, item=item)

@router.get("/{vocab_id}", response_model=schemas.VocabulaireResponse)
def read_vocab(vocab_id: int, db: Session = Depends(get_db)):
    db_vocab = crud.get_vocabulaire(db, vocab_id=vocab_id)
    if db_vocab is None:
        raise HTTPException(status_code=404, detail="Mot introuvable")
    return db_vocab