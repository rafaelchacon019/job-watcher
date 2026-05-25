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
    print(f"{index}. Title: {job.get('title', '')}")
    print(f"   Company: {job.get('company', '')}")
    print(f"   Portal: {job.get('portal', '')}")
    print(f"   Location: {job.get('location', '')}")
    print(f"   Modality: {job.get('modality', '')}")
    print(f"   Source: {job.get('source_type', '')}")
    print(f"   Link: {job.get('link', '')}")


def job_matches_keywords(job, keywords):
    """Revisa si una oferta contiene alguna palabra clave configurada."""
    if not keywords:
        return True

    text = " ".join(
        [
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("modality", ""),
            job.get("description", ""),
        ]
    ).lower()

    return any(str(keyword).lower() in text for keyword in keywords)


def filter_jobs_by_keywords(jobs, keywords):
    """Filtra ofertas ATS usando keywords opcionales."""
    return [job for job in jobs if job_matches_keywords(job, keywords)]


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
        max_results = int(settings.get("max_results", 10))

        jobs = []
        jobs.extend(fetch_greenhouse_jobs(greenhouse_companies))
        jobs.extend(fetch_lever_jobs(lever_companies))
        filtered_jobs = filter_jobs_by_keywords(jobs, keywords)
        shown_jobs = filtered_jobs[:max_results]

        print(f"Empresas Greenhouse configuradas: {len(greenhouse_companies)}")
        print(f"Empresas Lever configuradas: {len(lever_companies)}")
        print(f"Ofertas totales encontradas: {len(jobs)}")
        print(f"Ofertas filtradas por keywords: {len(filtered_jobs)}")
        print(f"Ofertas mostradas: {len(shown_jobs)}")

        for index, job in enumerate(shown_jobs, start=1):
            print_job(job, index)

    except RuntimeError as exc:
        print(f"Error durante la prueba ATS: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos: {exc}")


if __name__ == "__main__":
    main()
