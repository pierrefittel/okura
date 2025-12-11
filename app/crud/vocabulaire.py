from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models import vocabulaire as models
from app.schemas import vocabulaire as schemas

# --- Listes ---
def create_list(db: Session, list_data: schemas.VocabListCreate):
    db_list = models.VocabList(title=list_data.title, description=list_data.description)
    db.add(db_list)
    db.commit()
    db.refresh(db_list)
    return db_list

def get_lists(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.VocabList).offset(skip).limit(limit).all()

def get_list_with_cards(db: Session, list_id: int):
    return db.query(models.VocabList).filter(models.VocabList.id == list_id).first()

# --- Cartes & SRS ---

def get_due_cards(db: Session, limit: int = 50):
    """Récupère les cartes dont la date de révision est passée (ou est aujourd'hui)"""
    now = datetime.now()
    return db.query(models.VocabCard)\
             .filter(models.VocabCard.next_review <= now)\
             .order_by(models.VocabCard.next_review.asc())\
             .limit(limit)\
             .all()

def process_review(db: Session, card_id: int, quality: int):
    """
    Implémentation simplifiée de l'algorithme SM-2 (SuperMemo 2).
    quality: 0-5 (0=Blackout, 3=Passable, 5=Facile)
    """
    card = db.query(models.VocabCard).filter(models.VocabCard.id == card_id).first()
    if not card:
        return None

    if quality < 3:
        # Échec : On recommence à zéro
        card.streak = 0
        card.interval = 1
    else:
        # Succès
        if card.streak == 0:
            card.interval = 1
        elif card.streak == 1:
            card.interval = 6
        else:
            # Calcul exponentiel
            card.interval = int(card.interval * card.ease_factor)
        
        card.streak += 1
        
        # Ajustement du facteur de facilité (Ease Factor)
        # Formule SM-2 : EF' = EF + (0.1 - (5-q)*(0.08+(5-q)*0.02))
        card.ease_factor = card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if card.ease_factor < 1.3:
            card.ease_factor = 1.3

    # Mise à jour de la date
    card.next_review = datetime.now() + timedelta(days=card.interval)
    
    db.commit()
    db.refresh(card)
    return card

# --- Ajouts/Suppression ---
def add_card_to_list(db: Session, list_id: int, card_data: schemas.VocabCardCreate):
    defs_str = " | ".join(card_data.definitions) if card_data.definitions else ""
    db_card = models.VocabCard(
        list_id=list_id, ent_seq=card_data.ent_seq, terme=card_data.terme,
        lecture=card_data.lecture, pos=card_data.pos, definitions=defs_str
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def add_cards_to_list_bulk(db: Session, list_id: int, cards_data: list[schemas.VocabCardCreate]):
    existing_seqs = db.query(models.VocabCard.ent_seq).filter(models.VocabCard.list_id == list_id).all()
    existing_set = {s[0] for s in existing_seqs}
    new_cards = []
    processed_in_batch = set()

    for card in cards_data:
        if card.ent_seq is None or card.ent_seq in existing_set or card.ent_seq in processed_in_batch:
            continue
        
        defs_str = " | ".join(card.definitions) if card.definitions else ""
        db_card = models.VocabCard(
            list_id=list_id, ent_seq=card.ent_seq, terme=card.terme,
            lecture=card.lecture, pos=card.pos, definitions=defs_str
        )
        new_cards.append(db_card)
        processed_in_batch.add(card.ent_seq)

    if new_cards:
        db.add_all(new_cards)
        db.commit()
        for c in new_cards: db.refresh(c)
    return new_cards

def delete_card(db: Session, card_id: int):
    db_card = db.query(models.VocabCard).filter(models.VocabCard.id == card_id).first()
    if db_card:
        db.delete(db_card)
        db.commit()
        return True
    return False