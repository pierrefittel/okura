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

# --- NOUVEAU : IMPORT DE MASSE ---
def add_cards_to_list_bulk(db: Session, list_id: int, cards_data: list[schemas.VocabCardCreate]):
    # 1. On récupère les IDs (ent_seq) déjà présents dans cette liste
    # Cela évite les erreurs de contrainte UNIQUE SQL
    existing_seqs = db.query(models.VocabCard.ent_seq)\
                      .filter(models.VocabCard.list_id == list_id)\
                      .all()
    # On transforme le résultat [(123,), (456,)] en set {123, 456} pour la rapidité
    existing_set = {s[0] for s in existing_seqs}

    new_cards = []
    # On garde aussi un set local pour éviter les doublons DANS l'envoi lui-même
    processed_in_batch = set()

    for card in cards_data:
        # Si pas d'ID (mot inconnu) ou déjà en base ou déjà traité dans ce lot -> on saute
        if card.ent_seq is None:
            continue
        if card.ent_seq in existing_set:
            continue
        if card.ent_seq in processed_in_batch:
            continue
            
        defs_str = ""
        if card.definitions:
            defs_str = " | ".join(card.definitions)
        
        db_card = models.VocabCard(
            list_id=list_id,
            ent_seq=card.ent_seq,
            terme=card.terme,
            lecture=card.lecture,
            pos=card.pos,
            definitions=defs_str
        )
        new_cards.append(db_card)
        processed_in_batch.add(card.ent_seq)

    if new_cards:
        db.add_all(new_cards)
        db.commit()
        # On refresh pour récupérer les IDs générés par la DB
        for c in new_cards:
            db.refresh(c)
            
    return new_cards