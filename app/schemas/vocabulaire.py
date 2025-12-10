from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- PARTIE 1 : ANALYSE (Outil sans état) ---
# Ce sont les classes qui manquaient et causaient le crash
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

# --- PARTIE 2 : LISTES & CARTES (Base de données) ---

class VocabCardBase(BaseModel):
    terme: str
    lecture: Optional[str] = None
    pos: Optional[str] = None
    ent_seq: Optional[int] = None

class VocabCardCreate(VocabCardBase):
    # En entrée (création), on accepte une liste de définitions (ex: venant de l'analyse)
    definitions: List[str] = []

class VocabCardResponse(VocabCardBase):
    id: int
    list_id: int
    created_at: datetime
    # En sortie (lecture DB), c'est une chaîne de caractères concaténée
    definitions: Optional[str] = None

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