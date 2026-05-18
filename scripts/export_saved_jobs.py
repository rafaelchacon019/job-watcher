"""Exporta manualmente ofertas guardadas en SQLite a CSV.

Este script no lee correos, no usa IMAP y no guarda nuevas ofertas.
Solo toma lo que ya existe en data/jobs.db y genera un CSV en output/.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "output" / "ofertas_reales_priorizadas.csv"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_all_jobs
from src.email_parser import should_ignore_as_social_notification
from src.report import export_jobs_to_csv


def show_top_jobs(jobs):
    """Muestra maximo 5 ofertas exportadas."""
    print("Top 5 ofertas reales exportadas:")

    for index, job in enumerate(jobs[:5], start=1):
        print(f"{index}. Score: {job.get('score', 0)}")
        print(f"   Title: {job.get('title', '')}")
        print(f"   Company: {job.get('company', '')}")
        print(f"   Portal: {job.get('portal', '')}")
        print(f"   Location: {job.get('location', '')}")
        print(f"   Modality: {job.get('modality', '')}")


def main():
    """Lee ofertas guardadas y genera un CSV priorizado."""
    print("Exportacion manual de ofertas reales guardadas.")

    jobs = get_all_jobs()
    if not jobs:
        print("No hay ofertas guardadas para exportar.")
        return

    real_jobs = [
        job
        for job in jobs
        if (job.get("email_type") or "") == "job_alert"
        and not should_ignore_as_social_notification(
            job.get("title", ""),
            job.get("link", ""),
            job.get("description", ""),
        )
    ]
    ignored_jobs = len(jobs) - len(real_jobs)

    print(f"Ofertas totales en base: {len(jobs)}")

    if not real_jobs:
        print("No hay ofertas reales guardadas para exportar.")
        print(f"Ofertas ignoradas por no venir de correo: {ignored_jobs}")
        return

    sorted_jobs = sorted(real_jobs, key=lambda job: job.get("score", 0), reverse=True)
    csv_path = export_jobs_to_csv(sorted_jobs, OUTPUT_PATH)

    print(f"Ofertas reales exportadas: {len(sorted_jobs)}")
    print(f"Ofertas ignoradas por no venir de correo: {ignored_jobs}")
    print(f"CSV generado: {csv_path}")
    show_top_jobs(sorted_jobs)


if __name__ == "__main__":
    main()
