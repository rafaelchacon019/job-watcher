"""Prueba manual de scoring sobre correos parseados.

Este script no esta conectado a main.py. Lee correos filtrados solo si
email_settings.enabled es true, calcula puntajes en memoria y muestra un top.
No guarda en SQLite y no genera CSV.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.email_parser import parse_emails_to_jobs
from src.email_reader import read_recent_filtered_emails
from src.scorer import calculate_score


def load_config():
    """Carga config.yaml para usar email_settings y reglas de puntaje."""
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
    """Agrega score y reasons a cada posible oferta."""
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


def show_top_jobs(jobs):
    """Muestra un top corto sin imprimir cuerpos completos de correo."""
    print("Top de ofertas puntuadas:")

    job_alerts = [job for job in jobs if job.get("email_type") != "application_update"]
    application_updates = [
        job for job in jobs if job.get("email_type") == "application_update"
    ]

    for index, job in enumerate(job_alerts[:10], start=1):
        print(f"{index}. Score: {job.get('score', 0)}")
        print(f"   Type: {job.get('email_type', '')}")
        print(f"   Title: {job.get('title', '')}")
        print(f"   Company: {job.get('company', '')}")
        print(f"   Portal: {job.get('portal', '')}")
        print(f"   Location: {job.get('location', '')}")
        print(f"   Modality: {job.get('modality', '')}")
        print("   Reasons:")
        for reason in job.get("reasons", [])[:6]:
            print(f"   - {reason}")
        print(f"   Link: {job.get('link', '')}")

    if application_updates:
        print("Seguimientos de postulación detectados:")
        for index, job in enumerate(application_updates[:10], start=1):
            print(f"{index}. Score: {job.get('score', 0)}")
            print(f"   Type: {job.get('email_type', '')}")
            print(f"   Title: {job.get('title', '')}")
            print(f"   Company: {job.get('company', '')}")
            print(f"   Portal: {job.get('portal', '')}")
            print(f"   Location: {job.get('location', '')}")
            print(f"   Modality: {job.get('modality', '')}")
            print("   Reasons:")
            for reason in job.get("reasons", [])[:6]:
                print(f"   - {reason}")
            print(f"   Link: {job.get('link', '')}")


def main():
    """Ejecuta la prueba manual y controlada de scoring."""
    print("Prueba manual de scoring sobre correos parseados.")

    try:
        config = load_config()
        email_settings = config.get("email_settings", {})

        if not email_settings.get("enabled", False):
            print(
                "La lectura de correos está desactivada. "
                "Cambia email_settings.enabled a true para probar."
            )
            return

        emails = read_recent_filtered_emails(email_settings)
        jobs = parse_emails_to_jobs(emails)
        scored_jobs = score_jobs(jobs, config)

        print(f"Correos filtrados leídos: {len(emails)}")
        print(f"Posibles ofertas extraídas: {len(jobs)}")
        show_top_jobs(scored_jobs)

    except ValueError as exc:
        print(f"Configuración incompleta: {exc}")
    except ConnectionError as exc:
        print(f"Error de conexión o autenticación IMAP: {exc}")
    except RuntimeError as exc:
        print(f"Error durante la prueba de scoring: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos o red: {exc}")


if __name__ == "__main__":
    main()
