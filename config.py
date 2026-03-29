# config.py
# Fichier de configuration générale du projet
# On centralise ici tous les chemins et paramètres pour éviter de les répéter partout

import os
import logging
from pathlib import Path

# Chemin vers FFmpeg (à adapter selon votre installation)
FFMPEG_BIN = os.getenv("FFMPEG_BIN", r"E:\ffmpeg\bin\ffmpeg.exe")
FFPROBE_BIN = os.getenv("FFPROBE_BIN", r"E:\ffmpeg\bin\ffprobe.exe")

# Dossiers du projet
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
TMP_DIR = OUTPUT_DIR / "tmp"

# On crée les dossiers s'ils n'existent pas encore
for _d in (OUTPUT_DIR, REPORTS_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Paramètres du serveur
MAX_SIZE_MB = int(os.getenv("MAX_SIZE_MB", "50"))
BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:5001")
DEFAULT_PORT = int(os.getenv("PORT", "5001"))

# Liste des codecs qu'on supporte
SUPPORTED_CODECS = ["mp3", "aac", "ogg", "opus", "flac", "wav", "aiff"]

# Configuration du logging pour suivre ce qui se passe dans la console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("audio_api")
