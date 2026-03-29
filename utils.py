# utils.py
# Fonctions utilitaires qu'on réutilise dans plusieurs modules
# Ça évite de copier-coller le même code partout

import os
import uuid
import base64
import subprocess
from pathlib import Path
from typing import List, Tuple

from fastapi import HTTPException

from config import FFMPEG_BIN, MAX_SIZE_MB, logger


# --- Validation et nettoyage ---

def safe_float(value, default: float = 0.0) -> float:
    """Convertit en float sans planter si la valeur est invalide."""
    try:
        return float(value)
    except Exception:
        return default


def sanitize_filename(filename: str) -> str:
    """Nettoie le nom du fichier (enlève les espaces, les caractères bizarres, etc.)."""
    name = os.path.basename(filename).strip().replace(" ", "_")
    return name or f"audio_{uuid.uuid4().hex}.wav"


def ensure_file_size_ok(raw_bytes: bytes) -> None:
    """Vérifie que le fichier ne dépasse pas la taille max autorisée."""
    size_mb = len(raw_bytes) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux: {size_mb:.2f} MB > {MAX_SIZE_MB} MB",
        )


# --- Détection du format audio ---
# On regarde les premiers octets du fichier (magic bytes) pour identifier le vrai format,
# car parfois l'extension du fichier ne correspond pas au contenu réel.

def detect_audio_format(data: bytes) -> str:
    """Détecte le format audio à partir des magic bytes."""
    if len(data) < 12:
        return ""
    # WAV : commence par RIFF...WAVE
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ".wav"
    # MP3 : tag ID3 ou sync word
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa"):
        return ".mp3"
    # FLAC
    if data[:4] == b"fLaC":
        return ".flac"
    # OGG (Vorbis, Opus...)
    if data[:4] == b"OggS":
        return ".ogg"
    # M4A / AAC dans conteneur MP4
    if data[4:8] == b"ftyp":
        return ".m4a"
    # AIFF
    if data[:4] == b"FORM" and data[8:12] in (b"AIFF", b"AIFC"):
        return ".aiff"
    # AMR
    if data[:6] == b"#!AMR\n":
        return ".amr"
    # WMA
    if data[:4] == b"\x30\x26\xb2\x75":
        return ".wma"
    # AU / SND
    if data[:4] == b".snd":
        return ".au"
    # CAF
    if data[:4] == b"caff":
        return ".caf"
    # WebM
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return ".webm"
    return ""


# --- Gestion du base64 ---

def decode_audio_b64(file_base64: str, nom_fichier: str, tmp_dir: Path) -> Tuple[Path, int]:
    """Décode un fichier audio en base64 et le sauvegarde dans un dossier temporaire.
    On corrige aussi l'extension si elle ne correspond pas au vrai format."""
    try:
        audio_bytes = base64.b64decode(file_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Base64 invalide: {e}")

    ensure_file_size_ok(audio_bytes)
    filename = sanitize_filename(nom_fichier)

    # On vérifie que l'extension correspond bien au contenu réel
    detected_ext = detect_audio_format(audio_bytes)
    if detected_ext:
        current_ext = Path(filename).suffix.lower()
        if current_ext != detected_ext:
            logger.info(
                "[decode_b64] Extension corrigée: %s -> %s (détection magic bytes)",
                current_ext or "(aucune)", detected_ext,
            )
            filename = Path(filename).stem + detected_ext

    path = tmp_dir / filename
    path.write_bytes(audio_bytes)
    logger.info("[decode_b64] %s — %s octets", filename, len(audio_bytes))
    return path, len(audio_bytes)


def file_to_base64(path: Path) -> str:
    """Lit un fichier et le convertit en base64."""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


# --- FFmpeg ---

def run_ffmpeg(cmd: List[str]) -> None:
    """Lance une commande FFmpeg. Si ça échoue, on renvoie une erreur."""
    logger.info("FFmpeg: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "")[-1500:]
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {stderr}")


def convertir_en_wav(chemin_fichier: str) -> str:
    """Convertit n'importe quel fichier audio en WAV pour pouvoir l'analyser avec librosa.
    Si c'est déjà un vrai WAV, on le laisse tel quel."""
    # On vérifie le contenu réel, pas juste l'extension
    try:
        with open(chemin_fichier, "rb") as f:
            header = f.read(12)
        is_real_wav = (header[:4] == b"RIFF" and header[8:12] == b"WAVE")
    except Exception:
        is_real_wav = False

    if is_real_wav:
        return chemin_fichier

    # Sinon on convertit avec FFmpeg
    chemin_wav = chemin_fichier.rsplit(".", 1)[0] + "_converti.wav"
    try:
        run_ffmpeg([
            FFMPEG_BIN, "-y", "-i", chemin_fichier,
            chemin_wav,
        ])
        return chemin_wav
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Conversion WAV échouée")
        raise HTTPException(status_code=500, detail=f"Conversion audio échouée: {e}")
