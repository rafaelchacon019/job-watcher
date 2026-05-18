"""Prueba manual de notificaciones por consola y Telegram.

Este script no lee correos, no usa IMAP, no guarda ofertas y no genera CSV.
Solo notifica ofertas ya guardadas en SQLite que superan el puntaje minimo.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_all_jobs
from src.notifier import (
    get_jobs_for_notification,
    print_job_notifications,
    send_telegram_notifications,
)


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
        channels = settings.get("channels", {})
        console_enabled = channels.get("console", True)
        telegram_enabled = channels.get("telegram", False)
        candidate_jobs = [job for job in jobs if job.get("email_type") == "job_alert"]
        jobs_to_notify = get_jobs_for_notification(candidate_jobs, settings)
        console_notifications = 0
        telegram_sent = 0
        telegram_failed = 0

        print(f"Ofertas candidatas encontradas: {len(candidate_jobs)}")
        print(f"Ofertas que superan el puntaje minimo: {len(jobs_to_notify)}")

        if console_enabled:
            print_job_notifications(jobs_to_notify)
            console_notifications = len(jobs_to_notify)

        if telegram_enabled:
            try:
                telegram_summary = send_telegram_notifications(jobs_to_notify)
                telegram_sent = telegram_summary["enviados"]
                telegram_failed = telegram_summary["fallidos"]
            except ValueError as exc:
                print(f"Telegram no configurado: {exc}")
                telegram_failed = len(jobs_to_notify)

        print(f"Notificaciones por consola mostradas: {console_notifications}")
        print(f"Notificaciones Telegram enviadas: {telegram_sent}")
        print(f"Notificaciones Telegram fallidas: {telegram_failed}")

    except RuntimeError as exc:
        print(f"Error durante la prueba de notificaciones: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos: {exc}")


if __name__ == "__main__":
    main()
