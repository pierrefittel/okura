from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date

class ReviewAttempt(BaseModel):
    quality: int

class AnalyzeRequest(BaseModel):
    text: str

class AnalyzeResultItem(BaseModel):
    original: str
    terme: str
    lecture: str
    pos: str
    ent_seq: Optional[int] = None
    definitions: List[str] = []
    context: Optional[str] = None
    jlpt: Optional[int] = None # <-- NOUVEAU (5=N5, 1=N1, ou 0 si inconnu)

class AnalyzeResponse(BaseModel):
    candidates: List[AnalyzeResultItem]

class VocabCardBase(BaseModel):
    terme: str
    lecture: Optional[str] = None
    pos: Optional[str] = None
    ent_seq: Optional[int] = None
    context: Optional[str] = None
    # Note : On ne stocke pas forcément le JLPT en base pour l'instant, 
    # c'est surtout un outil de filtrage à l'entrée.

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