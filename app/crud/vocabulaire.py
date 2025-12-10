from sqlalchemy.orm import Session
from app.models import vocabulaire as models
from app.schemas import vocabulaire as schemas

def create_vocabulaire(db: Session, item: schemas.VocabulaireCreate):
    db_item = models.Vocabulaire(
        terme=item.terme,
        lecture=item.lecture,
        pos=item.pos,                   # <-- Nouveau
        langue=item.langue,
        definitions=item.definitions    # <-- Nouveau
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_vocabulaire(db: Session, vocab_id: int):
    return db.query(models.Vocabulaire).filter(models.Vocabulaire.id == vocab_id).first()