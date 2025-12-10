from sqlalchemy.orm import Session
from app.models import vocabulaire as models
from app.schemas import vocabulaire as schemas

# --- Listes ---
def create_list(db: Session, list_data: schemas.VocabListCreate):
    db_list = models.VocabList(
        title=list_data.title,
        description=list_data.description
    )
    db.add(db_list)
    db.commit()
    db.refresh(db_list)
    return db_list

def get_lists(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.VocabList).offset(skip).limit(limit).all()

def get_list_with_cards(db: Session, list_id: int):
    return db.query(models.VocabList).filter(models.VocabList.id == list_id).first()

# --- Cartes ---
def add_card_to_list(db: Session, list_id: int, card_data: schemas.VocabCardCreate):
    # Transformation de la liste de définitions en une seule chaîne pour le stockage simple
    defs_str = ""
    if card_data.definitions:
        defs_str = " | ".join(card_data.definitions)

    db_card = models.VocabCard(
        list_id=list_id,
        ent_seq=card_data.ent_seq,
        terme=card_data.terme,
        lecture=card_data.lecture,
        pos=card_data.pos,
        definitions=defs_str
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card