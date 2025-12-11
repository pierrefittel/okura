from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date

# --- SRS ---
class ReviewAttempt(BaseModel):
    quality: int

# --- ANALYSE ---
class AnalyzeRequest(BaseModel):
    text: str

class AnalyzeResultItem(BaseModel):
    original: str
    terme: str
    lecture: str
    pos: str
    ent_seq: Optional[int] = None
    definitions: List[str] = []
    context: Optional[str] = None # <-- NOUVEAU

class AnalyzeResponse(BaseModel):
    candidates: List[AnalyzeResultItem]

# --- MODEL DB ---
class VocabCardBase(BaseModel):
    terme: str
    lecture: Optional[str] = None
    pos: Optional[str] = None
    ent_seq: Optional[int] = None
    context: Optional[str] = None # <-- NOUVEAU

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

# --- LISTES ---
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

# --- DASHBOARD ---
class DashboardStats(BaseModel):
    total_cards: int
    cards_learned: int # Streak > 0
    due_today: int
    heatmap: Dict[str, int] # "YYYY-MM-DD": count