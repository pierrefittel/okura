from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# 1. Ce qui est commun (lecture et écriture)
class VocabulaireBase(BaseModel):
    terme: str
    lecture: Optional[str] = None
    langue: str  # 'JP' ou 'CN'

# 2. Ce qu'on attend de l'utilisateur pour CRÉER un mot
class VocabulaireCreate(VocabulaireBase):
    pass  # Rien de plus que la base pour l'instant

# 3. Ce que l'API renvoie (on ajoute l'ID et la date gérés par la DB)
class VocabulaireResponse(VocabulaireBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Permet de lire les objets SQLAlchemy

# Pour envoyer un texte à analyser
class AnalyzeRequest(BaseModel):
    text: str

# Ce que l'analyse renvoie pour un mot trouvé
class AnalyzeResultItem(BaseModel):
    original: str
    terme: str
    lecture: str
    pos: str
    definitions: List[str] = [] # <-- Ajout de ce champ

# La réponse complète de l'analyse
class AnalyzeResponse(BaseModel):
    candidates: List[AnalyzeResultItem]