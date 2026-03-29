# schemas.py
# Modèles de données pour valider les requêtes de l'API
# On utilise Pydantic pour s'assurer que les données envoyées sont correctes

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class AudioBase64Request(BaseModel):
    """Requête contenant un fichier audio en base64."""
    file_base64: str
    nom_fichier: str = "audio.wav"


class CompressionRequest(BaseModel):
    """Paramètres pour compresser un fichier audio."""
    file_base64: str
    nom_fichier: str = "audio.wav"
    codec: Literal["mp3", "aac", "ogg", "opus", "flac", "wav", "aiff"]
    bitrate: str = "128k"
    sample_rate: int = 44100
    channels: int = Field(default=2, ge=1, le=2)
    compression_level: int = Field(default=5, ge=0, le=12)
    decision: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None


class EvaluateRequest(BaseModel):
    """Données pour évaluer la qualité : on compare l'original au compressé."""
    original_file_base64: str
    original_nom_fichier: str = "original.wav"
    compressed_file_base64: str
    compressed_nom_fichier: str = "compressed.mp3"
    compression_result: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)
    analysis: Dict[str, Any] = Field(default_factory=dict)


class ReportRequest(BaseModel):
    """Données pour générer le rapport final."""
    analysis: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)
    compression: Dict[str, Any] = Field(default_factory=dict)
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    original_filename: str = "audio.wav"
    team_members: Optional[List[str]] = None
    notes: Optional[str] = None
