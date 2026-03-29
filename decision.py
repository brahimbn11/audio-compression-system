# decision.py
# Module de décision — Brahim Benazzouz
#
# Ce module choisit les meilleurs paramètres de compression selon le type de contenu.
# 
# Dans le mode n8n, c'est un agent LLM (Gemini) qui prend cette décision.
# Ici on a une version locale avec des règles qu'on a définies nous-mêmes,
# pour pouvoir tester sans avoir besoin du LLM.

from typing import Any, Dict


# Tableau de règles : pour chaque type de contenu, on définit le codec optimal,
# le bitrate, le sample rate et le nombre de canaux.
# On a choisi ces valeurs après nos recherches sur les codecs audio.

DECISION_RULES = {
    "speech": {
        "codec": "opus",
        "bitrate": "64k",
        "sample_rate": 44100,
        "channels": 1,
        "justification": "Voix humaine — Opus excelle pour la parole à faible bitrate.",
    },
    "podcast": {
        "codec": "opus",
        "bitrate": "96k",
        "sample_rate": 44100,
        "channels": 2,
        "justification": "Podcast — Opus offre une bonne qualité stéréo pour la voix.",
    },
    "audiobook": {
        "codec": "opus",
        "bitrate": "48k",
        "sample_rate": 44100,
        "channels": 1,
        "justification": "Audiobook — signal simple, mono, faible bitrate suffisant.",
    },
    "classical_music": {
        "codec": "flac",
        "bitrate": "256k",
        "sample_rate": 44100,
        "channels": 2,
        "justification": "Musique classique — FLAC préserve la dynamique et les harmoniques.",
    },
    "music": {
        "codec": "aac",
        "bitrate": "192k",
        "sample_rate": 44100,
        "channels": 2,
        "justification": "Musique générale — AAC offre un bon compromis qualité/taille.",
    },
    "electronic_music": {
        "codec": "aac",
        "bitrate": "256k",
        "sample_rate": 44100,
        "channels": 2,
        "justification": "Musique électronique — hautes fréquences, bitrate élevé requis.",
    },
    "noise": {
        "codec": "mp3",
        "bitrate": "64k",
        "sample_rate": 44100,
        "channels": 1,
        "justification": "Bruit / ambiance — contenu peu complexe, compression forte possible.",
    },
    "mixed": {
        "codec": "aac",
        "bitrate": "128k",
        "sample_rate": 44100,
        "channels": 2,
        "justification": "Contenu mixte — AAC polyvalent avec bitrate intermédiaire.",
    },
}


def decider_parametres(decision_input: Dict[str, Any]) -> Dict[str, Any]:
    """Choisit les paramètres de compression à partir des caractéristiques extraites.
    
    On récupère le type de contenu détecté par l'extraction,
    puis on applique les règles du tableau ci-dessus.
    On fait aussi quelques ajustements dynamiques selon le cas."""

    content_type = decision_input.get("content_type", "music")
    spectral_centroid = decision_input.get("spectral_centroid", 0)

    # On prend les règles par défaut pour ce type de contenu
    rules = DECISION_RULES.get(content_type, DECISION_RULES["music"])

    # Si le centroïde spectral est élevé (beaucoup de hautes fréquences),
    # on augmente le bitrate pour mieux les préserver
    bitrate = rules["bitrate"]
    if spectral_centroid > 3000 and content_type in ("music", "electronic_music", "mixed"):
        bitrate_val = int(bitrate.replace("k", ""))
        bitrate = f"{min(bitrate_val + 64, 320)}k"

    codec = rules["codec"]

    # Protection : si le fichier source est déjà en lossy (mp3, aac...),
    # ça ne sert à rien de le convertir en FLAC ou WAV car on ne récupère
    # pas la qualité perdue, et en plus ça gonfle la taille du fichier
    format_origine = decision_input.get("format_origine", "unknown")
    lossy_formats = {"mp3", "aac", "ogg", "opus", "m4a", "wma", "amr", "webm"}
    if codec in ("flac", "wav") and format_origine in lossy_formats:
        codec = "aac"
        bitrate = "256k"

    return {
        "content_type_detected": content_type,
        "codec": codec,
        "bitrate": bitrate,
        "sample_rate": rules["sample_rate"],
        "channels": rules["channels"],
        "justification": rules["justification"],
    }
