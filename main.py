# main.py
# Point d'entrée de l'API — Serveur FastAPI
#
# Ce fichier rassemble tous les modules et crée les endpoints de l'API.
# Il est compatible avec le workflow n8n (mêmes URLs, mêmes formats JSON).
#
# Pour lancer : python main.py
# La doc interactive sera sur http://localhost:5001/docs

import os
import uuid
import base64

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from config import (
    OUTPUT_DIR, REPORTS_DIR, TMP_DIR, BASE_URL,
    DEFAULT_PORT, SUPPORTED_CODECS, logger,
)
from schemas import (
    AudioBase64Request,
    CompressionRequest,
    EvaluateRequest,
    ReportRequest,
)
from utils import sanitize_filename, ensure_file_size_ok, file_to_base64
from extraction import analyser_fichier
from compression import compress_audio
from evaluation import evaluate_audio
from report import generate_report


# --- Création de l'application FastAPI ---

app = FastAPI(
    title="Système Intelligent de Compression Audio",
    description=(
        "API complète: extraction + compression + évaluation + rapport.\n\n"
        "Projet IRM — Université Hassan II, FSTM.\n\n"
        "Formats supportés : wav, mp3, m4a, flac, aac, ogg, opus, aiff, wma, amr, webm..."
    ),
    version="3.0.0",
)


# --- Endpoints d'extraction (Omar) ---

@app.post("/extract", summary="Extraction par upload de fichier")
async def extract_features(file: UploadFile = File(...)):
    """Upload un fichier audio et retourne ses caractéristiques."""
    temp_path = TMP_DIR / f"upload_{uuid.uuid4().hex}_{sanitize_filename(file.filename)}"
    raw = await file.read()
    ensure_file_size_ok(raw)
    temp_path.write_bytes(raw)
    try:
        result = await analyser_fichier(str(temp_path), file.filename)
        return JSONResponse(content=result)
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.post("/extract_base64", summary="Extraction par base64")
async def extract_base64_endpoint(req: AudioBase64Request):
    """Même chose mais avec le fichier encodé en base64 (utilisé par le frontend)."""
    temp_path = TMP_DIR / f"b64_{uuid.uuid4().hex}_{sanitize_filename(req.nom_fichier)}"
    try:
        audio_bytes = base64.b64decode(req.file_base64)
        ensure_file_size_ok(audio_bytes)
        temp_path.write_bytes(audio_bytes)
        result = await analyser_fichier(str(temp_path), req.nom_fichier)
        return JSONResponse(content=result)
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.post("/extract_for_decision", summary="Extraction format decision_input")
async def extract_for_decision(req: AudioBase64Request):
    """Retourne uniquement le decision_input (utilisé par l'agent LLM dans n8n)."""
    temp_path = TMP_DIR / f"decision_{uuid.uuid4().hex}_{sanitize_filename(req.nom_fichier)}"
    try:
        audio_bytes = base64.b64decode(req.file_base64)
        ensure_file_size_ok(audio_bytes)
        temp_path.write_bytes(audio_bytes)
        result = await analyser_fichier(str(temp_path), req.nom_fichier)
        return JSONResponse(content=result["decision_input"])
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.post("/extract_and_decide", summary="Extraction + Décision sans LLM")
async def extract_and_decide(req: AudioBase64Request):
    """Analyse le fichier et prend la décision de compression directement (mode local)."""
    from decision import decider_parametres

    temp_path = TMP_DIR / f"decide_{uuid.uuid4().hex}_{sanitize_filename(req.nom_fichier)}"
    try:
        audio_bytes = base64.b64decode(req.file_base64)
        ensure_file_size_ok(audio_bytes)
        temp_path.write_bytes(audio_bytes)
        result = await analyser_fichier(str(temp_path), req.nom_fichier)
        decision = decider_parametres(result["decision_input"])
        return JSONResponse(content={
            "extraction": result,
            "decision": decision,
        })
    finally:
        if temp_path.exists():
            temp_path.unlink()


# --- Endpoint de compression (Hamza) ---

@app.post("/compress", summary="Compression audio")
async def compress_endpoint(req: CompressionRequest):
    """Compresse le fichier audio avec les paramètres donnés."""
    result = compress_audio(req)
    return JSONResponse(content=result)


# --- Endpoint d'évaluation (Rida) ---

@app.post("/evaluate", summary="Évaluation de qualité")
async def evaluate_endpoint(req: EvaluateRequest):
    """Compare l'original et le compressé, retourne les métriques de qualité."""
    result = evaluate_audio(req)
    return JSONResponse(content=result)


# --- Endpoint de rapport ---

@app.post("/report", summary="Génération de rapport")
async def report_endpoint(req: ReportRequest):
    """Génère le rapport final en JSON + CSV."""
    result = generate_report(req)
    return JSONResponse(content=result)


# --- Endpoints de téléchargement ---

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Télécharge un fichier compressé."""
    safe_name = os.path.basename(filename)
    path = OUTPUT_DIR / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable: {safe_name}")
    return JSONResponse({
        "nom_fichier": safe_name,
        "taille_bytes": path.stat().st_size,
        "file_base64": file_to_base64(path),
    })


@app.get("/download/reports/{filename}")
async def download_report_file(filename: str):
    """Télécharge un rapport JSON."""
    safe_name = os.path.basename(filename)
    path = REPORTS_DIR / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Rapport introuvable: {safe_name}")
    return JSONResponse({
        "nom_fichier": safe_name,
        "taille_bytes": path.stat().st_size,
        "file_base64": file_to_base64(path),
    })


# --- Health check ---

@app.get("/health")
async def health():
    """Vérifie que l'API fonctionne correctement."""
    return {
        "statut": "ok",
        "message": "API audio active",
        "version": "3.0.0",
        "base_url": BASE_URL,
        "output_dir": str(OUTPUT_DIR),
        "endpoints": {
            "analysis": ["/extract", "/extract_base64", "/extract_for_decision"],
            "compression": ["/compress"],
            "evaluation": ["/evaluate"],
            "report": ["/report"],
            "download": ["/download/{filename}", "/download/reports/{filename}"],
        },
        "supported_codecs": SUPPORTED_CODECS,
        "equipe": [
            "Brahim Benazzouz — Architecture & LLM",
            "Omar El Haddad — Extraction & Analyse",
            "Boukhar Hamza — Compression",
            "Afkir Rida — Évaluation & Rapport",
        ],
    }


# --- Lancement du serveur ---

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("API de compression audio démarrée")
    logger.info("Port       : %s", DEFAULT_PORT)
    logger.info("Output dir : %s", OUTPUT_DIR)
    logger.info("Docs       : http://localhost:%s/docs", DEFAULT_PORT)
    logger.info("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
