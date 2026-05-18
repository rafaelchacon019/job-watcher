"""Prueba manual de notificaciones por consola.

Este script no lee correos, no usa IMAP, no guarda ofertas y no genera CSV.
Solo muestra ofertas ya guardadas en SQLite que superan el puntaje minimo.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_all_jobs
from src.notifier import get_jobs_for_notification, print_job_notifications


def load_config():
    """Carga config.yaml para leer notification_settings."""
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


def main():
    """Ejecuta notificaciones locales sobre ofertas ya guardadas."""
    print("Notificaciones manuales de ofertas guardadas.")

    try:
        config = load_config()
        settings = config.get("notification_settings", {})

        if not settings.get("enabled", False):
            print(
                "Las notificaciones estan desactivadas. "
                "Cambia notification_settings.enabled a true para probar."
            )
            return

        jobs = get_all_jobs()
        candidate_jobs = [job for job in jobs if job.get("email_type") == "job_alert"]
        jobs_to_notify = get_jobs_for_notification(candidate_jobs, settings)

        print(f"Ofertas candidatas encontradas: {len(candidate_jobs)}")
        print(f"Ofertas que superan el puntaje minimo: {len(jobs_to_notify)}")
        print_job_notifications(jobs_to_notify)

    except RuntimeError as exc:
        print(f"Error durante la prueba de notificaciones: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos: {exc}")


if __name__ == "__main__":
    main()
