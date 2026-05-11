"""Punto de entrada de job-watcher."""

from pathlib import Path

from src.database import get_all_jobs, init_db, save_job
from src.parser import get_sample_jobs
from src.report import export_jobs_to_csv
from src.scorer import calculate_score


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
CSV_PATH = BASE_DIR / "output" / "ofertas_priorizadas.csv"


def load_config():
    """Carga la configuracion YAML del proyecto."""
    try:
        import yaml
    except ModuleNotFoundError:
        print("Falta instalar dependencias. Ejecuta: pip install -r requirements.txt")
        raise SystemExit(1)

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def main():
    """Ejecuta la Fase 1 usando ofertas locales de prueba."""
    print("Iniciando job-watcher - Fase 1 local...")

    config = load_config()
    init_db()

    sample_jobs = get_sample_jobs()
    for job in sample_jobs:
        score_result = calculate_score(job, config)
        job_with_score = {
            **job,
            "score": score_result["score"],
            "reasons": score_result["reasons"],
        }
        save_job(job_with_score)

    saved_jobs = get_all_jobs()
    csv_path = export_jobs_to_csv(saved_jobs, CSV_PATH)

    print(f"Ofertas procesadas: {len(sample_jobs)}")
    print("Top de mejores ofertas:")
    for index, job in enumerate(saved_jobs[:5], start=1):
        print(
            f"{index}. {job['title']} - {job['company']} "
            f"({job['score']} puntos)"
        )

    print(f"CSV generado: {csv_path}")


if __name__ == "__main__":
    main()
