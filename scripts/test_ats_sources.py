"""Prueba manual de fuentes ATS publicas.

Este script no guarda en SQLite, no envia Telegram y no se conecta al worker.
Solo consulta empresas configuradas cuando ats_sources.enabled esta en true.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sources.greenhouse_source import fetch_greenhouse_jobs
from src.sources.lever_source import fetch_lever_jobs
from src.sources.base_source import (
    build_ats_scoring_config,
    filter_jobs_by_exclusions,
    filter_jobs_by_keywords,
    get_int_setting,
)
from src.scorer import calculate_score


def load_config():
    """Carga config.yaml para leer ats_sources."""
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


def print_job(job, index):
    """Muestra una oferta normalizada sin guardar nada."""
    reasons = job.get("reasons", [])[:5]

    print(f"{index}. Score: {job.get('score', 0)}")
    print(f"   Title: {job.get('title', '')}")
    print(f"   Company: {job.get('company', '')}")
    print(f"   Portal: {job.get('portal', '')}")
    print(f"   Location: {job.get('location', '')}")
    print(f"   Modality: {job.get('modality', '')}")
    print(f"   Source: {job.get('source_type', '')}")
    print("   Reasons:")
    for reason in reasons:
        print(f"   - {reason}")
    print(f"   Link: {job.get('link', '')}")


def score_jobs(jobs, config):
    """Calcula score de ofertas ATS sin guardar resultados."""
    scored_jobs = []

    for job in jobs:
        score_result = calculate_score(job, config)
        scored_jobs.append(
            {
                **job,
                "score": score_result["score"],
                "reasons": score_result["reasons"],
            }
        )

    return scored_jobs


def main():
    """Ejecuta la prueba manual de fuentes ATS."""
    print("Prueba manual de fuentes ATS publicas.")

    try:
        config = load_config()
        settings = config.get("ats_sources", {})

        if not settings.get("enabled", False):
            print(
                "Las fuentes ATS estan desactivadas. "
                "Cambia ats_sources.enabled a true para probar."
            )
            return

        greenhouse_companies = settings.get("greenhouse_companies", [])
        lever_companies = settings.get("lever_companies", [])
        keywords = settings.get("keywords", [])
        exclude_keywords = settings.get("exclude_keywords", [])
        max_results = get_int_setting(settings, "max_results", 10)
        min_score = get_int_setting(settings, "min_score", 20)
        scoring_config = build_ats_scoring_config(config, settings)

        jobs = []
        jobs.extend(fetch_greenhouse_jobs(greenhouse_companies))
        jobs.extend(fetch_lever_jobs(lever_companies))
        keyword_jobs = filter_jobs_by_keywords(jobs, keywords)
        target_jobs, excluded_count = filter_jobs_by_exclusions(
            keyword_jobs,
            exclude_keywords,
        )
        scored_jobs = score_jobs(target_jobs, scoring_config)
        enough_score_jobs = [
            job for job in scored_jobs if job.get("score", 0) >= min_score
        ]
        sorted_jobs = sorted(
            enough_score_jobs,
            key=lambda job: job.get("score", 0),
            reverse=True,
        )
        shown_jobs = sorted_jobs[:max_results]

        print(f"Empresas Greenhouse configuradas: {len(greenhouse_companies)}")
        print(f"Empresas Lever configuradas: {len(lever_companies)}")
        print(f"Ofertas totales encontradas: {len(jobs)}")
        print(f"Filtradas por keywords: {len(keyword_jobs)}")
        print(f"Excluidas por palabras no objetivo: {excluded_count}")
        print(f"Con score suficiente: {len(enough_score_jobs)}")
        print(f"Ofertas mostradas: {len(shown_jobs)}")

        for index, job in enumerate(shown_jobs, start=1):
            print_job(job, index)

    except RuntimeError as exc:
        print(f"Error durante la prueba ATS: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos: {exc}")


if __name__ == "__main__":
    main()
