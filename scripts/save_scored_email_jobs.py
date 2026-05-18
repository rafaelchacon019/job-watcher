"""Guarda manualmente ofertas reales puntuadas desde correos.

Este script no esta conectado a main.py. Lee correos filtrados solo si
email_settings.enabled es true, guarda solo ofertas tipo job_alert con score
mayor a 0 y no genera CSV.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import init_db, save_job_if_not_exists
from src.email_parser import parse_emails_to_jobs, should_ignore_as_social_notification
from src.email_reader import read_recent_filtered_emails
from src.scorer import calculate_score


def load_config():
    """Carga config.yaml para leer email_settings y reglas de puntaje."""
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


def score_jobs(jobs, config):
    """Calcula score y reasons para cada posible oferta."""
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

    return sorted(scored_jobs, key=lambda job: job["score"], reverse=True)


def save_scored_jobs(scored_jobs):
    """Guarda solo ofertas nuevas y cuenta las no guardadas."""
    summary = {
        "saved": 0,
        "duplicate_or_not_saved": 0,
        "application_updates": 0,
        "discarded_score_zero": 0,
        "saved_jobs": [],
        "processed_jobs": [],
    }

    for job in scored_jobs:
        summary["processed_jobs"].append(job)

        if job.get("email_type") == "application_update":
            summary["application_updates"] += 1
            continue

        if job.get("email_type") != "job_alert":
            summary["duplicate_or_not_saved"] += 1
            continue

        if job.get("score", 0) <= 0:
            summary["discarded_score_zero"] += 1
            continue

        if not job.get("link"):
            summary["duplicate_or_not_saved"] += 1
            continue

        if should_ignore_as_social_notification(
            job.get("title", ""),
            job.get("link", ""),
            job.get("description", ""),
        ):
            summary["duplicate_or_not_saved"] += 1
            continue

        job_to_save = {
            **job,
            "email_type": "job_alert",
        }

        if save_job_if_not_exists(job_to_save):
            summary["saved"] += 1
            summary["saved_jobs"].append(job_to_save)
        else:
            summary["duplicate_or_not_saved"] += 1

    return summary


def show_top_jobs(jobs):
    """Muestra maximo 5 ofertas sin imprimir cuerpos completos de correo."""
    print("Top 5 ofertas guardadas o procesadas:")

    for index, job in enumerate(jobs[:5], start=1):
        print(f"{index}. Score: {job.get('score', 0)}")
        print(f"   Title: {job.get('title', '')}")
        print(f"   Company: {job.get('company', '')}")
        print(f"   Portal: {job.get('portal', '')}")
        print(f"   Location: {job.get('location', '')}")
        print(f"   Modality: {job.get('modality', '')}")
        print(f"   Link: {job.get('link', '')}")


def main():
    """Ejecuta el guardado manual y controlado de ofertas puntuadas."""
    print("Guardado manual de ofertas puntuadas desde correos.")

    try:
        config = load_config()
        email_settings = config.get("email_settings", {})

        if not email_settings.get("enabled", False):
            print(
                "La lectura de correos está desactivada. "
                "Cambia email_settings.enabled a true para probar."
            )
            return

        init_db()
        emails = read_recent_filtered_emails(email_settings)
        jobs = parse_emails_to_jobs(emails)
        scored_jobs = score_jobs(jobs, config)
        summary = save_scored_jobs(scored_jobs)

        print(f"Correos filtrados leídos: {len(emails)}")
        print(f"Posibles ofertas extraídas: {len(jobs)}")
        print(f"Ofertas guardadas: {summary['saved']}")
        print(
            "Ofertas duplicadas o no guardadas: "
            f"{summary['duplicate_or_not_saved']}"
        )
        print(f"Seguimientos detectados: {summary['application_updates']}")
        print(f"Ofertas descartadas por score 0: {summary['discarded_score_zero']}")

        top_jobs = summary["saved_jobs"] or summary["processed_jobs"]
        show_top_jobs(top_jobs)

    except ValueError as exc:
        print(f"Configuración incompleta: {exc}")
    except ConnectionError as exc:
        print(f"Error de conexión o autenticación IMAP: {exc}")
    except RuntimeError as exc:
        print(f"Error durante el guardado manual: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos o red: {exc}")


if __name__ == "__main__":
    main()
