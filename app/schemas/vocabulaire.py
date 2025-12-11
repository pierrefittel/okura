from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date

# --- SRS ---
class ReviewAttempt(BaseModel):
    quality: int

# --- ANALYSE ---
class AnalyzeRequest(BaseModel):
    text: str

class AnalyzedToken(BaseModel):
    text: str                
    is_word: bool = False    
    
    # Données enrichies (si is_word=True)
    lemma: Optional[str] = None
    reading: Optional[str] = None
    pos: Optional[str] = None
    ent_seq: Optional[int] = None
    definitions: List[str] = []
    jlpt: Optional[int] = None

class AnalyzeResponse(BaseModel):
    # Liste de phrases, chaque phrase est une liste de tokens
    sentences: List[List[AnalyzedToken]]

# --- MODEL DB ---
class VocabCardBase(BaseModel):
    terme: str
    lecture: Optional[str] = None
    pos: Optional[str] = None
    ent_seq: Optional[int] = None
    context: Optional[str] = None

class VocabCardCreate(VocabCardBase):
    definitions: List[str] = []

class VocabCardResponse(VocabCardBase):
    id: int
    list_id: int
    created_at: datetime
    definitions: Optional[str] = None
    next_review: Optional[datetime] = None
    streak: int = 0
    class Config:
        from_attributes = True

# --- LISTES & DASHBOARD ---
class VocabListBase(BaseModel):
    title: str
    description: Optional[str] = None

class VocabListCreate(VocabListBase):
    pass

class VocabListResponse(VocabListBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class VocabListWithCards(VocabListResponse):
    cards: List[VocabCardResponse] = []

class DashboardStats(BaseModel):
    total_cards: int
    cards_learned: int
    due_today: int
    heatmap: Dict[str, int]