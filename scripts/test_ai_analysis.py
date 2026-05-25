"""Prueba manual de analisis IA sobre ofertas guardadas.

Este script no guarda resultados en SQLite, no envia Telegram y no modifica el
worker. Solo analiza ofertas ya guardadas si ai_settings.enabled esta en true.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_analyzer import analyze_jobs_batch
from src.database import get_all_jobs


def load_config():
    """Carga config.yaml para leer ai_settings."""
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Falta instalar PyYAML. Ejecuta: pip install -r requirements.txt"
        ) from exc

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError("No se pudo interpretar config.yaml. Revisa el YAML.") from exc


def get_candidate_jobs(jobs, settings):
    """Filtra ofertas guardadas que cumplen score minimo para IA."""
    min_score = int(settings.get("min_score", 20))
    max_jobs = int(settings.get("max_jobs_per_cycle", 3))
    candidates = [
        job
        for job in jobs
        if job.get("email_type") == "job_alert"
        and int(job.get("score", 0) or 0) >= min_score
    ]
    return candidates[:max_jobs]


def print_analysis_result(result, index):
    """Muestra un analisis IA sin guardar nada."""
    job = result["job"]
    analysis = result["analysis"]

    print(f"{index}. Score: {job.get('score', 0)}")
    print(f"   Title: {job.get('title', '')}")
    print(f"   Company: {job.get('company', '')}")
    print(f"   Portal: {job.get('portal', '')}")
    print(f"   Resumen IA: {analysis.get('summary', '')}")
    print(f"   Compatibilidad: {analysis.get('match_level', '')}")
    print(f"   Seniority estimado: {analysis.get('estimated_seniority', '')}")
    print(f"   Stack detectado: {', '.join(analysis.get('detected_stack', []))}")
    print(f"   Modalidad IA: {analysis.get('work_modality', '')}")
    print(f"   Riesgos: {', '.join(analysis.get('red_flags', []))}")
    print(f"   Recomendacion: {analysis.get('recommendation', '')}")
    print(f"   Link: {job.get('link', '')}")


def main():
    """Ejecuta la prueba manual de analisis IA."""
    print("Prueba manual de analisis IA para ofertas guardadas.")

    try:
        config = load_config()
        ai_settings = config.get("ai_settings", {})

        if not ai_settings.get("enabled", False):
            print(
                "La IA esta desactivada. "
                "Cambia ai_settings.enabled a true para probar."
            )
            return

        jobs = get_all_jobs()
        candidates = get_candidate_jobs(jobs, ai_settings)

        if not candidates:
            print("No hay ofertas guardadas con score suficiente para analizar.")
            return

        print(f"Ofertas candidatas para IA: {len(candidates)}")
        results = analyze_jobs_batch(candidates, config)

        for index, result in enumerate(results, start=1):
            print_analysis_result(result, index)

    except ValueError as exc:
        print(f"Advertencia de configuracion IA: {exc}")
    except RuntimeError as exc:
        print(f"Advertencia durante analisis IA: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos: {exc}")


if __name__ == "__main__":
    main()
