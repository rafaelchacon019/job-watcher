"""Generacion de reportes locales."""

import csv
from pathlib import Path


def export_jobs_to_csv(jobs, output_path):
    """Exporta las ofertas priorizadas a un archivo CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "title",
        "company",
        "portal",
        "location",
        "modality",
        "score",
        "reasons",
        "link",
    ]

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for job in jobs:
            writer.writerow(
                {
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "portal": job.get("portal", ""),
                    "location": job.get("location", ""),
                    "modality": job.get("modality", ""),
                    "score": job.get("score", 0),
                    "reasons": "; ".join(job.get("reasons", [])),
                    "link": job.get("link", ""),
                }
            )

    return path
