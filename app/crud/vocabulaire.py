import csv
import io
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from app.models import vocabulaire as models
from app.schemas import vocabulaire as schemas

# --- GESTION DES LISTES ---
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

# --- NOUVEAU : SUPPRESSION DE LISTE ---
def delete_list(db: Session, list_id: int):
    db_list = db.query(models.VocabList).filter(models.VocabList.id == list_id).first()
    if db_list:
        db.delete(db_list)
        db.commit()
        return True
    return False

# --- CARTES & SRS ---
def get_due_cards(db: Session, limit: int = 50, list_id: int = None):
    now = datetime.now()
    query = db.query(models.VocabCard).filter(models.VocabCard.next_review <= now)
    if list_id:
        query = query.filter(models.VocabCard.list_id == list_id)
    return query.order_by(models.VocabCard.next_review.asc()).limit(limit).all()

def process_review(db: Session, card_id: int, quality: int):
    card = db.query(models.VocabCard).filter(models.VocabCard.id == card_id).first()
    if not card: return None

    if quality < 3:
        # ÉCHEC : On reset à 0 pour qu'il reste "Due Today"
        card.streak = 0
        card.interval = 0 
    else:
        # SUCCÈS
        if card.streak == 0: card.interval = 1
        elif card.streak == 1: card.interval = 6
        else: card.interval = int(card.interval * card.ease_factor)
        
        card.streak += 1
        # Ajustement Ease Factor
        card.ease_factor = max(1.3, card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

    # Si interval = 0, next_review = maintenant (donc toujours "À réviser")
    card.next_review = datetime.now() + timedelta(days=card.interval)
    
    # Log Stats
    today = date.today()
    log = db.query(models.ReviewLog).filter(models.ReviewLog.date == today).first()
    if not log:
        log = models.ReviewLog(date=today, reviewed_count=0)
        db.add(log)
    log.reviewed_count += 1
    
    db.commit()
    db.refresh(card)
    return card

# --- DASHBOARD ---
def get_dashboard_stats(db: Session):
    total = db.query(models.VocabCard).count()
    learned = db.query(models.VocabCard).filter(models.VocabCard.streak > 0).count()
    # Due today inclut désormais les cartes ratées aujourd'hui (car next_review <= now)
    due = db.query(models.VocabCard).filter(models.VocabCard.next_review <= datetime.now()).count()
    
    logs = db.query(models.ReviewLog).order_by(models.ReviewLog.date.desc()).limit(60).all()
    heatmap = {str(log.date): log.reviewed_count for log in logs}
    return {"total_cards": total, "cards_learned": learned, "due_today": due, "heatmap": heatmap}

# --- BULK & CRUD ---
def add_cards_to_list_bulk(db: Session, list_id: int, cards_data: list[schemas.VocabCardCreate]):
    existing = {s[0] for s in db.query(models.VocabCard.ent_seq).filter(models.VocabCard.list_id == list_id).all()}
    new_cards, processed = [], set()
    for card in cards_data:
        if card.ent_seq and card.ent_seq not in existing and card.ent_seq not in processed:
            defs = " | ".join(card.definitions) if isinstance(card.definitions, list) else card.definitions
            new_cards.append(models.VocabCard(
                list_id=list_id, ent_seq=card.ent_seq, terme=card.terme,
                lecture=card.lecture, pos=card.pos, definitions=defs, context=card.context
            ))
            processed.add(card.ent_seq)
    if new_cards:
        db.add_all(new_cards)
        db.commit()
        for c in new_cards: db.refresh(c)
    return new_cards

def add_card_to_list(db: Session, list_id: int, card_data: schemas.VocabCardCreate):
    defs = " | ".join(card_data.definitions) if isinstance(card_data.definitions, list) else card_data.definitions
    c = models.VocabCard(
        list_id=list_id, ent_seq=card_data.ent_seq, terme=card_data.terme,
        lecture=card_data.lecture, pos=card_data.pos, definitions=defs, context=card_data.context
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def delete_card(db: Session, card_id: int):
    c = db.query(models.VocabCard).filter(models.VocabCard.id == card_id).first()
    if c:
        db.delete(c)
        db.commit()
        return True
    return False

# --- EXPORT / IMPORT CSV ---
def export_to_csv(db: Session) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['list_title', 'terme', 'lecture', 'pos', 'definitions', 'context', 'ent_seq', 'streak', 'interval', 'next_review'])
    cards = db.query(models.VocabCard).join(models.VocabList).all()
    for c in cards:
        writer.writerow([
            c.vocab_list.title, c.terme, c.lecture, c.pos, c.definitions, c.context or "",
            c.ent_seq or "", c.streak, c.interval, c.next_review.isoformat() if c.next_review else ""
        ])
    return output.getvalue()

def import_from_csv(db: Session, csv_content: str):
    f = io.StringIO(csv_content)
    reader = csv.DictReader(f)
    stats = {"cards_created": 0, "lists_created": 0, "errors": 0}
    lists_cache = {l.title: l for l in db.query(models.VocabList).all()}
    
    for row in reader:
        try:
            list_title = row.get('list_title', 'Import Default')
            if list_title not in lists_cache:
                new_list = models.VocabList(title=list_title, description="Importé via CSV")
                db.add(new_list)
                db.commit()
                db.refresh(new_list)
                lists_cache[list_title] = new_list
                stats["lists_created"] += 1
            
            current_list = lists_cache[list_title]
            exists = db.query(models.VocabCard).filter(
                models.VocabCard.list_id == current_list.id,
                models.VocabCard.terme == row['terme']
            ).first()
            
            if not exists:
                ent_seq = int(row['ent_seq']) if row.get('ent_seq') else None
                new_card = models.VocabCard(
                    list_id=current_list.id, terme=row['terme'], lecture=row.get('lecture'),
                    pos=row.get('pos'), definitions=row.get('definitions'), context=row.get('context'),
                    ent_seq=ent_seq, streak=int(row.get('streak', 0)), interval=int(row.get('interval', 0))
                )
                db.add(new_card)
                stats["cards_created"] += 1
        except Exception as e:
            stats["errors"] += 1
            
    db.commit()
    return stats