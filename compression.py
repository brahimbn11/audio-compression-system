# compression.py
# Module de compression audio — Boukhar Hamza
#
# Ce module gère la compression des fichiers audio avec FFmpeg.
# Il supporte : MP3, AAC, OGG, Opus, FLAC, WAV, AIFF
# Chaque codec a ses propres paramètres FFmpeg.

import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException

from config import FFMPEG_BIN, OUTPUT_DIR, TMP_DIR, BASE_URL, logger
from schemas import CompressionRequest
from utils import decode_audio_b64, file_to_base64, run_ffmpeg, sanitize_filename


# --- Configuration des codecs ---
# Pour chaque codec, on retourne l'extension du fichier et les arguments FFmpeg correspondants

def codec_config(codec: str, bitrate: str, compression_level: int) -> Tuple[str, List[str]]:
    """Retourne l'extension et les paramètres FFmpeg pour le codec choisi."""
    codec = codec.lower().strip()
    if codec == "mp3":
        return ".mp3", ["-c:a", "libmp3lame", "-b:a", bitrate]
    if codec == "aac":
        return ".m4a", ["-c:a", "aac", "-b:a", bitrate]
    if codec == "ogg":
        return ".ogg", ["-c:a", "libvorbis", "-b:a", bitrate]
    if codec == "opus":
        return ".opus", ["-c:a", "libopus", "-b:a", bitrate]
    if codec == "flac":
        level = str(max(0, min(compression_level, 12)))
        return ".flac", ["-c:a", "flac", "-compression_level", level]
    if codec == "wav":
        return ".wav", ["-c:a", "pcm_s16le"]
    if codec == "aiff":
        return ".aiff", ["-c:a", "pcm_s16be"]
    raise HTTPException(status_code=400, detail=f"Codec non supporté: {codec}")


def build_compressed_filename(source_name: str, codec: str) -> str:
    """Génère le nom du fichier compressé avec un timestamp pour éviter les doublons."""
    stem = Path(source_name).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix_map = {
        "mp3": ".mp3",
        "aac": ".m4a",
        "ogg": ".ogg",
        "opus": ".opus",
        "flac": ".flac",
        "wav": ".wav",
        "aiff": ".aiff",
    }
    ext = suffix_map.get(codec, f".{codec}")
    return f"{stem}_{codec}_{timestamp}{ext}"


# --- Fonction principale de compression ---

def compress_audio(req: CompressionRequest) -> Dict[str, Any]:
    """Compresse un fichier audio avec les paramètres donnés.
    
    Étapes :
    1. Décoder le fichier base64
    2. Construire la commande FFmpeg avec les bons paramètres
    3. Lancer la compression
    4. Sauvegarder le résultat et calculer le taux de compression"""

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tmp:
        tmp_dir = Path(tmp)
        input_path, original_size = decode_audio_b64(req.file_base64, req.nom_fichier, tmp_dir)

        ext, ffmpeg_codec_args = codec_config(req.codec, req.bitrate, req.compression_level)
        output_filename = build_compressed_filename(req.nom_fichier, req.codec)
        output_tmp_path = tmp_dir / output_filename

        # Construction de la commande FFmpeg
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", str(input_path),
            "-ar", str(req.sample_rate),     # sample rate
            "-ac", str(req.channels),         # nombre de canaux
            *ffmpeg_codec_args,               # codec + bitrate
            str(output_tmp_path),
        ]
        run_ffmpeg(cmd)

        # Copier le fichier compressé dans le dossier output
        final_path = OUTPUT_DIR / output_filename
        shutil.copy2(output_tmp_path, final_path)

        # Calcul du taux de compression
        compressed_size = final_path.stat().st_size
        taux = round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0.0

        logger.info(
            "[compression] %s → %s (%s) — taux=%.2f%%",
            req.nom_fichier, output_filename, req.codec, taux,
        )

        return {
            "statut": "succes",
            "format": req.codec,
            "nom_fichier_source": sanitize_filename(req.nom_fichier),
            "nom_fichier_compresse": output_filename,
            "file_base64_compresse": file_to_base64(final_path),
            "download_url": f"{BASE_URL}/download/{output_filename}",
            "taille_originale_bytes": int(original_size),
            "taille_compressee_bytes": int(compressed_size),
            "taux_compression_pct": float(taux),
            "parametres_appliques": {
                "codec": req.codec,
                "bitrate": req.bitrate,
                "sample_rate": req.sample_rate,
                "channels": req.channels,
                "compression_level": req.compression_level if req.codec == "flac" else None,
            },
            "decision_recue": req.decision or {},
            "analysis_reference": req.analysis or {},
        }
