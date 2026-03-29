# extraction.py
# Module d'extraction des caractéristiques audio — Omar El Haddad
# 
# Ce module s'occupe de :
# - Charger le fichier audio (n'importe quel format)
# - Extraire les métadonnées (durée, taille, sample rate, canaux)
# - Calculer les caractéristiques audio (RMS, ZCR, centroïde spectral, MFCC, etc.)
# - Classifier le type de contenu (parole, musique, podcast...)

import os
from pathlib import Path
from typing import Any, Dict, List

import librosa
import numpy as np

from config import logger
from utils import sanitize_filename, convertir_en_wav


# --- Calculs spectraux ---

def spectral_entropy(y: np.ndarray) -> float:
    """Calcule l'entropie spectrale du signal.
    Plus l'entropie est haute, plus le signal est complexe/aléatoire (ex: bruit).
    Plus elle est basse, plus le signal est structuré (ex: parole, musique tonale)."""
    spectrum = np.abs(librosa.stft(y)) ** 2
    ps = np.mean(spectrum, axis=1)
    ps_sum = np.sum(ps)
    if ps_sum <= 0:
        return 0.0
    ps = ps / ps_sum
    ps = np.clip(ps, 1e-12, None)
    ent = -np.sum(ps * np.log2(ps))
    return float(ent / np.log2(len(ps))) if len(ps) > 1 else 0.0


def dynamic_range_db(y: np.ndarray) -> float:
    """Calcule la plage dynamique en dB (différence entre le son le plus fort et le plus faible).
    Utile pour distinguer la musique classique (grande dynamique) de la parole (faible dynamique)."""
    y_abs = np.abs(y)
    peak = np.max(y_abs) if len(y_abs) else 0.0
    floor = np.percentile(y_abs, 10) if len(y_abs) else 0.0
    floor = max(floor, 1e-8)
    peak = max(peak, 1e-8)
    return float(20 * np.log10(peak / floor))


# --- Classification du type audio ---
# On classe le contenu en fonction des caractéristiques extraites.
# L'ordre des tests est important : on vérifie d'abord la parole car
# elle peut être confondue avec de la musique classique (les deux ont
# un centroïde bas et une grande dynamique quand il y a des silences).

def classifier_type_audio(
    zcr: float,
    centroid: float,
    bandwidth: float,
    entropie: float,
    rms: float,
    dynamic_range: float,
    mfcc: List[float],
) -> str:
    """Classifie le type de contenu audio.
    Retourne : audiobook, podcast, speech, classical_music, electronic_music, music, noise, ou mixed."""

    # Voix / Parole — on teste en premier pour éviter les faux positifs
    if zcr < 0.05 and centroid < 1500 and bandwidth < 2000 and dynamic_range < 15:
        return "audiobook"
    if zcr < 0.08 and centroid < 2000 and bandwidth < 2500 and entropie < 0.5:
        return "podcast"
    if centroid < 2200 and bandwidth < 2800 and entropie < 0.65:
        return "speech"

    # Musique et autres catégories
    if dynamic_range > 25 and centroid < 2500 and bandwidth > 2000 and entropie > 0.6:
        return "classical_music"
    if centroid > 3000 and bandwidth > 3000 and zcr > 0.08:
        return "electronic_music"
    if entropie > 0.85 and rms < 0.08:
        return "noise"
    if 0.06 < zcr < 0.14 and 1500 < centroid < 3500:
        return "mixed"
    if centroid < 2200 and bandwidth < 2800:
        return "speech"
    return "music"


# --- Fonction principale d'analyse ---

async def analyser_fichier(chemin_fichier: str, nom_fichier: str) -> Dict[str, Any]:
    """Analyse complète d'un fichier audio.
    Retourne toutes les métadonnées, caractéristiques et la classification."""
    
    fichier_converti = False
    chemin_wav = convertir_en_wav(chemin_fichier)
    if chemin_wav != chemin_fichier:
        fichier_converti = True

    try:
        # Chargement du fichier avec librosa
        y, sr = librosa.load(chemin_wav, sr=None, mono=False)

        if y.ndim == 1:
            y_mono = y
            channels = 1
        else:
            channels = y.shape[0]
            y_mono = librosa.to_mono(y)

        # Métadonnées de base
        taille_bytes = os.path.getsize(chemin_fichier)
        duree = librosa.get_duration(y=y_mono, sr=sr)

        # Extraction des caractéristiques audio
        rms = float(np.mean(librosa.feature.rms(y=y_mono)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y_mono)))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y_mono, sr=sr)))
        bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y_mono, sr=sr)))
        mfcc_values = librosa.feature.mfcc(y=y_mono, sr=sr, n_mfcc=13)
        mfcc_means = [float(np.mean(row)) for row in mfcc_values]
        entropie = spectral_entropy(y_mono)
        dyn_range = dynamic_range_db(y_mono)
        tempo_result, _ = librosa.beat.beat_track(y=y_mono, sr=sr)
        tempo = float(np.atleast_1d(tempo_result)[0]) if np.ndim(tempo_result) > 0 else float(tempo_result)

        # Classification du contenu
        type_audio = classifier_type_audio(
            zcr=zcr,
            centroid=centroid,
            bandwidth=bandwidth,
            entropie=entropie,
            rms=rms,
            dynamic_range=dyn_range,
            mfcc=mfcc_means,
        )

        logger.info(
            "[extraction] %s — durée=%.2fs, sr=%d, type=%s",
            nom_fichier, duree, sr, type_audio,
        )

        # On retourne tout sous forme de dictionnaire
        return {
            "statut": "succes",
            "nom_fichier": sanitize_filename(nom_fichier),
            "metadonnees": {
                "taille_bytes": taille_bytes,
                "duree_secondes": round(float(duree), 2),
                "sample_rate": int(sr),
                "channels": int(channels),
                "format_origine": Path(nom_fichier).suffix.lower().replace(".", "") or "unknown",
            },
            "caracteristiques": {
                "rms_energy": round(rms, 6),
                "zero_crossing_rate": round(zcr, 6),
                "spectral_centroid": round(centroid, 2),
                "spectral_bandwidth": round(bandwidth, 2),
                "spectral_entropy": round(entropie, 6),
                "dynamic_range_db": round(dyn_range, 2),
                "tempo": round(float(tempo), 2),
                "mfcc": [round(v, 4) for v in mfcc_means],
            },
            "analyse": {
                "type_audio": type_audio,
            },
            # Ce format simplifié est utilisé par le module de décision
            "decision_input": {
                "duration": round(float(duree), 2),
                "sample_rate": int(sr),
                "channels": int(channels),
                "file_size": int(taille_bytes),
                "rms_energy": round(rms, 6),
                "spectral_centroid": round(centroid, 2),
                "zero_crossing_rate": round(zcr, 4),
                "content_type": type_audio,
                "format_origine": Path(nom_fichier).suffix.lower().replace(".", "") or "unknown",
            },
        }
    finally:
        # Nettoyage du fichier temporaire si on a fait une conversion
        if fichier_converti and os.path.exists(chemin_wav):
            os.remove(chemin_wav)
