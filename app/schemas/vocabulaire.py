from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# 1. Base commune
class VocabulaireBase(BaseModel):
    terme: str
    lecture: Optional[str] = None
    pos: Optional[str] = None           # <-- Nouveau
    langue: str = "JP"
    definitions: List[str] = []         # <-- Nouveau

# 2. Création (Rien de plus que la base)
class VocabulaireCreate(VocabulaireBase):
    pass

# 3. Réponse API
class VocabulaireResponse(VocabulaireBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Partie Analyse (inchangée, mais compatible désormais) ---
class AnalyzeRequest(BaseModel):
    text: str

class AnalyzeResultItem(BaseModel):
    original: str
    terme: str
    lecture: str
    pos: str
    ent_seq: Optional[int] = None  # <--- AJOUT CRUCIAL
    definitions: List[str] = []

class AnalyzeResponse(BaseModel):
    candidates: List[AnalyzeResultItem]