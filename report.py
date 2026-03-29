# report.py
# Module de génération de rapports
#
# Génère un rapport JSON détaillé à la fin du pipeline et
# ajoute une ligne dans un fichier CSV récapitulatif.
# Le CSV permet de garder un historique de toutes les compressions.

import csv
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

from config import REPORTS_DIR, BASE_URL, logger
from schemas import ReportRequest


# --- Utilitaires pour le CSV ---

def flatten_for_csv(data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """Aplatit un dictionnaire imbriqué en un seul niveau.
    Par exemple : {"a": {"b": 1}} devient {"a.b": 1}
    C'est nécessaire car le CSV ne supporte pas les données imbriquées."""
    items: Dict[str, Any] = {}
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_for_csv(value, new_key, sep=sep))
        elif isinstance(value, list):
            items[new_key] = json.dumps(value, ensure_ascii=False)
        else:
            items[new_key] = value
    return items


def append_report_csv(report_data: Dict[str, Any], csv_path: Path) -> None:
    """Ajoute une ligne au fichier CSV récapitulatif.
    Crée le fichier avec les en-têtes si c'est la première fois."""
    flat = flatten_for_csv(report_data)
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(flat)


# --- Fonction principale de rapport ---

def generate_report(req: ReportRequest) -> Dict[str, Any]:
    """Génère le rapport final avec toutes les données du pipeline.
    
    Le rapport contient : les infos d'analyse, la décision prise,
    les résultats de compression, les métriques d'évaluation,
    et un résumé des points clés."""

    # ID unique pour ce rapport
    report_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    report_filename = f"report_{report_id}.json"
    csv_filename = "reports_summary.csv"

    # Construction du rapport
    report_data = {
        "statut": "succes",
        "report_id": report_id,
        "generated_at": datetime.now().isoformat(),
        "project": "Système Intelligent de Compression Audio",
        "original_filename": req.original_filename,
        "team_members": req.team_members or [
            "Brahim Benazzouz",
            "Omar El Haddad",
            "Boukhar Hamza",
            "Afkir Rida",
        ],
        "analysis": req.analysis,
        "decision": req.decision,
        "compression": req.compression,
        "evaluation": req.evaluation,
        "notes": req.notes,
        # Résumé rapide des résultats les plus importants
        "summary": {
            "content_type": (
                req.decision.get("content_type_detected")
                or req.analysis.get("analyse", {}).get("type_audio")
            ),
            "codec": req.compression.get("format") or req.decision.get("codec"),
            "bitrate": (
                req.compression.get("parametres_appliques", {}).get("bitrate")
                or req.decision.get("bitrate")
            ),
            "sample_rate": (
                req.compression.get("parametres_appliques", {}).get("sample_rate")
                or req.decision.get("sample_rate")
            ),
            "channels": (
                req.compression.get("parametres_appliques", {}).get("channels")
                or req.decision.get("channels")
            ),
            "compression_ratio_pct": (
                req.evaluation.get("evaluation", {}).get("taux_compression_pct")
                if isinstance(req.evaluation.get("evaluation"), dict)
                else req.evaluation.get("taux_compression_pct")
            ),
            "snr_db": (
                req.evaluation.get("evaluation", {}).get("snr_db")
                if isinstance(req.evaluation.get("evaluation"), dict)
                else req.evaluation.get("snr_db")
            ),
            "psnr_db": (
                req.evaluation.get("evaluation", {}).get("psnr_db")
                if isinstance(req.evaluation.get("evaluation"), dict)
                else req.evaluation.get("psnr_db")
            ),
        },
    }

    # Sauvegarde du rapport JSON
    json_path = REPORTS_DIR / report_filename
    csv_path = REPORTS_DIR / csv_filename

    json_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Ajout au CSV récapitulatif
    append_report_csv(report_data, csv_path)

    logger.info("[rapport] %s généré", report_id)

    return {
        "statut": "succes",
        "report_id": report_id,
        "report_json": report_data,
        "report_json_filename": report_filename,
        "report_json_download_url": f"{BASE_URL}/download/reports/{report_filename}",
        "report_csv_filename": csv_filename,
        "report_csv_download_url": f"{BASE_URL}/download/reports/{csv_filename}",
    }
