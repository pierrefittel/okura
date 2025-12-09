from sqlalchemy.orm import Session
from app.models import vocabulaire as models
from app.schemas import vocabulaire as schemas

def create_vocabulaire(db: Session, item: schemas.VocabulaireCreate):
    # On transforme le schema Pydantic en modèle SQLAlchemy
    db_item = models.Vocabulaire(
        terme=item.terme,
        lecture=item.lecture,
        langue=item.langue
    )
    db.add(db_item)
    db.commit()      # On valide la transaction
    db.refresh(db_item) # On récupère l'ID généré par la DB
    return db_item

def get_vocabulaire(db: Session, vocab_id: int):
    return db.query(models.Vocabulaire).filter(models.Vocabulaire.id == vocab_id).first()