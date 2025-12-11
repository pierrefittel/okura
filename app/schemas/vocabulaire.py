from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- SRS ---
class ReviewAttempt(BaseModel):
    quality: int # 0=Oubli total, 3=Ok, 5=Parfait

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

class AnalyzeResponse(BaseModel):
    candidates: List[AnalyzeResultItem]

# --- MODEL DB ---
class VocabCardBase(BaseModel):
    terme: str
    lecture: Optional[str] = None
    pos: Optional[str] = None
    ent_seq: Optional[int] = None

class VocabCardCreate(VocabCardBase):
    definitions: List[str] = []

class VocabCardResponse(VocabCardBase):
    id: int
    list_id: int
    created_at: datetime
    definitions: Optional[str] = None
    
    # Champs SRS visibles
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