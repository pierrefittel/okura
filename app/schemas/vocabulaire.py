from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date

class ReviewAttempt(BaseModel):
    quality: int

class AnalyzeRequest(BaseModel):
    text: str
    lang: str = "jp"

class AnalyzedToken(BaseModel):
    text: str
    is_word: bool = False
    lemma: Optional[str] = None
    reading: Optional[str] = None
    pos: Optional[str] = None
    ent_seq: Optional[int] = None
    definitions: List[str] = []
    jlpt: Optional[int] = None

class AnalyzeResponse(BaseModel):
    sentences: List[List[AnalyzedToken]]
    raw_text: Optional[str] = None # <-- NOUVEAU : Pour renvoyer le texte extrait

# --- MODEL DB (Inchangé) ---
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

class VocabListBase(BaseModel):
    title: str
    description: Optional[str] = None
    lang: str = "jp"

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

class AnalysisBase(BaseModel):
    title: str
    content: str
    lang: str = "jp"

class AnalysisCreate(AnalysisBase):
    pass

class AnalysisResponse(AnalysisBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True