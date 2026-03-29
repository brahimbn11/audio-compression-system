# 🎵 Système Intelligent de Compression Audio

> Projet académique — Licence IRM, Université Hassan II, FSTM (2025-2026)

## 📋 Description

Système multi-agents de compression audio intelligente qui analyse automatiquement un fichier audio, détermine les meilleurs paramètres de compression, applique la compression, évalue la qualité du résultat et génère un rapport détaillé.

Le système utilise une architecture modulaire basée sur une API REST (FastAPI) avec une interface web interactive (Streamlit).

## 🏗️ Architecture

```
📁 audio_compression/
│
├── main.py              # Serveur FastAPI — point d'entrée de l'API
├── config.py            # Configuration centralisée (chemins, logging)
├── schemas.py           # Modèles Pydantic — validation des données
├── utils.py             # Fonctions utilitaires partagées
│
├── extraction.py        # Agent 1 : Extraction & analyse des caractéristiques
├── decision.py          # Agent 2 : Décision des paramètres de compression
├── compression.py       # Agent 3 : Compression audio via FFmpeg
├── evaluation.py        # Agent 4 : Évaluation de la qualité (SNR, PSNR, corrélation)
├── report.py            # Agent 5 : Génération du rapport JSON
│
├── streamlit_app.py     # Interface web interactive
├── requirements.txt     # Dépendances Python
├── .env                 # Variables d'environnement (non versionné)
└── logo.jpeg            # Logo de l'université
```

## 🔄 Pipeline de traitement

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Extraction  │───▶│  Décision   │───▶│ Compression │───▶│ Évaluation  │───▶│   Rapport   │
│   (Omar)     │    │  (Brahim)   │    │   (Hamza)   │    │   (Rida)    │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

1. **Extraction** — Analyse du fichier audio : métadonnées, caractéristiques spectrales, classification du contenu (parole, musique, etc.)
2. **Décision** — Choix automatique du codec, bitrate, sample rate et nombre de canaux optimaux
3. **Compression** — Application de la compression via FFmpeg avec les paramètres choisis
4. **Évaluation** — Comparaison original vs compressé : SNR, PSNR, corrélation, taux de compression
5. **Rapport** — Génération d'un rapport JSON complet avec toutes les métriques

## 👥 Équipe

| Membre | Rôle |
|--------|------|
| **Brahim Benazzouz** (chef) | Architecture & Intégration LLM |
| **Omar El Haddad** | Extraction & Analyse audio |
| **Boukhar Hamza** | Compression audio |
| **Afkir Rida** | Évaluation & Rapport |

## 🚀 Installation

### Prérequis

- Python 3.9+
- FFmpeg installé et accessible dans le PATH (ou configuré dans `config.py`)

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/VOTRE_USERNAME/audio-compression.git
cd audio-compression

# 2. Créer un environnement virtuel
python -m venv venv

# 3. Activer l'environnement virtuel
# Windows :
.\venv\Scripts\activate
# Linux/Mac :
source venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt
```

## ▶️ Utilisation

### Lancer l'API

```bash
python main.py
```

L'API sera disponible sur `http://localhost:5001`.

### Lancer l'interface Streamlit

Dans un second terminal :

```bash
streamlit run streamlit_app.py
```

L'interface sera disponible sur `http://localhost:8501`.

### Mode n8n (optionnel)

Pour utiliser le mode n8n avec un agent LLM :

1. Lancer ngrok : `ngrok http 5001`
2. Configurer l'URL ngrok dans le workflow n8n
3. Sélectionner le mode "n8n (Webhook)" dans l'interface Streamlit

## 📡 Endpoints de l'API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Vérification de l'état de l'API |
| `POST` | `/extract_base64` | Extraction des caractéristiques audio |
| `POST` | `/compress` | Compression du fichier audio |
| `POST` | `/evaluate` | Évaluation de la qualité |
| `POST` | `/report` | Génération du rapport |

## 📊 Métriques d'évaluation

- **SNR** (Signal-to-Noise Ratio) — rapport signal/bruit en dB
- **PSNR** (Peak Signal-to-Noise Ratio) — rapport signal/bruit crête en dB
- **Corrélation** — coefficient de Pearson entre les signaux (0 à 1)
- **MSE** (Mean Squared Error) — erreur quadratique moyenne
- **MAE** (Mean Absolute Error) — erreur absolue moyenne
- **Taux de compression** — réduction de taille en pourcentage

## 🛠️ Technologies utilisées

- **Python** — Langage principal
- **FastAPI** — Framework API REST
- **Streamlit** — Interface web interactive
- **Librosa** — Analyse audio
- **NumPy** — Calculs numériques
- **FFmpeg** — Compression audio
- **Plotly** — Visualisations interactives
- **Pydantic** — Validation des données
- **n8n** — Orchestration workflow (optionnel)

## 📄 Licence

Projet académique — Université Hassan II, Faculté des Sciences et Techniques de Mohammedia.
Licence Informatique, Réseaux et Multimédia (IRM) — 2025-2026.
