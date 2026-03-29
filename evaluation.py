# evaluation.py
# Module d'évaluation de la qualité — Afkir Rida
#
# Ce module compare le fichier original avec le fichier compressé
# pour mesurer la perte de qualité. On calcule plusieurs métriques :
# - SNR (rapport signal/bruit)
# - PSNR (rapport signal/bruit crête)
# - MSE et MAE (erreurs moyennes)
# - Corrélation entre les deux signaux
# - Taux de compression

import os
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple

import librosa
import numpy as np

from config import TMP_DIR, logger
from schemas import EvaluateRequest
from utils import decode_audio_b64, convertir_en_wav


# --- Chargement et préparation des signaux ---

def load_audio_mono_preserve_sr(path: Path) -> Tuple[np.ndarray, int]:
    """Charge un fichier audio en mono en gardant son sample rate original."""
    wav_path = convertir_en_wav(str(path))
    try:
        y, sr = librosa.load(wav_path, sr=None, mono=True)
        return y.astype(np.float32), sr
    finally:
        if wav_path != str(path) and os.path.exists(wav_path):
            os.remove(wav_path)


def resample_if_needed(y: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    """Si les deux fichiers ont des sample rates différents, on rééchantillonne
    le compressé pour pouvoir les comparer correctement."""
    if source_sr == target_sr:
        return y
    return librosa.resample(y, orig_sr=source_sr, target_sr=target_sr)


def align_signals(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """On coupe les deux signaux à la même longueur (le plus court des deux)."""
    n = min(len(a), len(b))
    if n == 0:
        return np.zeros(1, dtype=np.float32), np.zeros(1, dtype=np.float32)
    return a[:n], b[:n]


# --- Calcul des métriques ---

def compute_snr_db(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """Calcule le SNR (Signal-to-Noise Ratio) en dB.
    Plus c'est élevé, mieux c'est. Le "bruit" c'est la différence entre les deux signaux."""
    noise = original - reconstructed
    signal_power = float(np.mean(original ** 2))
    noise_power = float(np.mean(noise ** 2))
    if noise_power <= 1e-12:
        return 99.99  # pas de bruit = qualité parfaite
    if signal_power <= 1e-12:
        return 0.0
    return float(10 * np.log10(signal_power / noise_power))


def compute_psnr_db(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """Calcule le PSNR (Peak Signal-to-Noise Ratio) en dB.
    C'est comme le SNR mais basé sur la valeur crête du signal."""
    mse = float(np.mean((original - reconstructed) ** 2))
    if mse <= 1e-12:
        return 99.99
    peak = max(float(np.max(np.abs(original))), 1e-8)
    return float(20 * np.log10(peak / math.sqrt(mse)))


# --- Fonction principale d'évaluation ---

def evaluate_audio(req: EvaluateRequest) -> Dict[str, Any]:
    """Compare l'original et le compressé, calcule toutes les métriques,
    et donne une note de qualité globale (bonne, moyenne ou faible)."""

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tmp:
        tmp_dir = Path(tmp)

        # Décodage des deux fichiers
        original_path, original_size = decode_audio_b64(
            req.original_file_base64,
            req.original_nom_fichier,
            tmp_dir,
        )
        compressed_path, compressed_size_raw = decode_audio_b64(
            req.compressed_file_base64,
            req.compressed_nom_fichier,
            tmp_dir,
        )

        # Chargement et alignement des signaux
        y_orig, sr_orig = load_audio_mono_preserve_sr(original_path)
        y_comp, sr_comp = load_audio_mono_preserve_sr(compressed_path)
        y_comp = resample_if_needed(y_comp, sr_comp, sr_orig)
        y_orig, y_comp = align_signals(y_orig, y_comp)

        # Calcul de toutes les métriques
        snr_db = round(compute_snr_db(y_orig, y_comp), 2)
        psnr_db = round(compute_psnr_db(y_orig, y_comp), 2)
        mse = round(float(np.mean((y_orig - y_comp) ** 2)), 8)
        mae = round(float(np.mean(np.abs(y_orig - y_comp))), 8)
        correlation = round(float(np.corrcoef(y_orig, y_comp)[0, 1]), 6) if len(y_orig) > 1 else 0.0
        taux = round((1 - compressed_size_raw / original_size) * 100, 2) if original_size > 0 else 0.0

        # Attribution de la note de qualité
        # On utilise la corrélation comme critère principal car c'est plus fiable
        # que le SNR. En effet, quand on change le sample rate ou les canaux pendant
        # la compression, le SNR baisse alors que l'audio reste identique à l'oreille.
        # La corrélation mesure mieux si les deux signaux "se ressemblent" vraiment.
        if correlation >= 0.999:
            quality_label = "bonne"
        elif correlation >= 0.99:
            if snr_db >= 20:
                quality_label = "bonne"
            else:
                quality_label = "moyenne"
        elif correlation >= 0.95:
            quality_label = "moyenne"
        else:
            quality_label = "faible"

        logger.info(
            "[évaluation] SNR=%.2f dB, PSNR=%.2f dB, qualité=%s, taux=%.2f%%",
            snr_db, psnr_db, quality_label, taux,
        )

        return {
            "statut": "succes",
            "evaluation": {
                "snr_db": snr_db,
                "psnr_db": psnr_db,
                "mse": mse,
                "mae": mae,
                "correlation": correlation,
                "taux_compression_pct": taux,
                "qualite_estimee": quality_label,
                "duree_comparee_secondes": round(len(y_orig) / sr_orig, 2) if sr_orig > 0 else 0.0,
                "sample_rate_reference": sr_orig,
            },
            "decision_reference": req.decision,
            "analysis_reference": req.analysis,
            "compression_reference": req.compression_result,
        }
