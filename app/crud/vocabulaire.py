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

def get_vocabulaires(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Vocabulaire).offset(skip).limit(limit).all()

def create_vocabulaire_bulk(db: Session, items: list[schemas.VocabulaireCreate]):
    db_items = [
        models.Vocabulaire(
            terme=item.terme,
            lecture=item.lecture,
            pos=item.pos,
            langue=item.langue,
            definitions=item.definitions
        )
        for item in items
    ]
    db.add_all(db_items)
    db.commit()
    # Pour récupérer les IDs générés, c'est plus coûteux en performance, 
    # mais pour <100 mots ça va.
    for item in db_items:
        db.refresh(item)
    return db_items