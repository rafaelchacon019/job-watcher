"""Worker local para ejecutar job-watcher de forma periodica.

Este script no esta conectado a main.py. Lee correos solo si email_settings y
worker_settings estan activos, guarda nuevas ofertas reales y notifica si aplica.
No genera CSV.
"""

import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import init_db, save_job_if_not_exists
from src.email_parser import parse_emails_to_jobs, should_ignore_as_social_notification
from src.email_reader import read_recent_filtered_emails
from src.notifier import (
    get_jobs_for_notification,
    print_job_notifications,
    send_telegram_notifications,
)
from src.scorer import calculate_score


def load_config():
    """Carga config.yaml con la configuracion del worker."""
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

    return scored_jobs


def should_save_job(job):
    """Valida si una oferta debe guardarse como oferta real."""
    if job.get("email_type") != "job_alert":
        return False
    if job.get("score", 0) <= 0:
        return False
    if not job.get("link"):
        return False
    if should_ignore_as_social_notification(
        job.get("title", ""),
        job.get("link", ""),
        job.get("description", ""),
    ):
        return False

    return True


def save_new_jobs(scored_jobs):
    """Guarda ofertas nuevas y separa duplicadas o ignoradas."""
    summary = {
        "new_jobs": [],
        "duplicates": 0,
        "ignored": 0,
    }

    for job in scored_jobs:
        if not should_save_job(job):
            summary["ignored"] += 1
            continue

        job_to_save = {
            **job,
            "email_type": "job_alert",
        }

        if save_job_if_not_exists(job_to_save):
            summary["new_jobs"].append(job_to_save)
        else:
            summary["duplicates"] += 1

    return summary


def notify_new_jobs(new_jobs, notification_settings):
    """Notifica ofertas nuevas segun configuracion de canales."""
    summary = {
        "candidates": 0,
        "console": 0,
        "telegram_sent": 0,
        "telegram_failed": 0,
    }

    if not notification_settings.get("enabled", False):
        print("Notificaciones desactivadas en notification_settings.enabled.")
        return summary

    jobs_to_notify = get_jobs_for_notification(new_jobs, notification_settings)
    channels = notification_settings.get("channels", {})
    console_enabled = channels.get("console", True)
    telegram_enabled = channels.get("telegram", False)
    summary["candidates"] = len(jobs_to_notify)

    if console_enabled:
        print_job_notifications(jobs_to_notify)
        summary["console"] = len(jobs_to_notify)

    if telegram_enabled:
        try:
            telegram_summary = send_telegram_notifications(jobs_to_notify)
            summary["telegram_sent"] = telegram_summary["enviados"]
            summary["telegram_failed"] = telegram_summary["fallidos"]
        except ValueError as exc:
            print(f"Telegram no configurado: {exc}")
            summary["telegram_failed"] = len(jobs_to_notify)

    return summary


def run_once(config):
    """Ejecuta una pasada completa del worker."""
    email_settings = config.get("email_settings", {})
    notification_settings = config.get("notification_settings", {})

    if not email_settings.get("enabled", False):
        print("La lectura de correos esta desactivada en email_settings.enabled.")
        return

    init_db()

    emails = read_recent_filtered_emails(email_settings)
    jobs = parse_emails_to_jobs(emails)
    scored_jobs = score_jobs(jobs, config)
    save_summary = save_new_jobs(scored_jobs)
    notification_summary = notify_new_jobs(
        save_summary["new_jobs"],
        notification_settings,
    )

    print(f"Correos leidos: {len(emails)}")
    print(f"Ofertas parseadas: {len(jobs)}")
    print(f"Ofertas nuevas guardadas: {len(save_summary['new_jobs'])}")
    print(f"Duplicadas ignoradas: {save_summary['duplicates']}")
    print(f"Ofertas ignoradas por filtros: {save_summary['ignored']}")
    print(f"Notificaciones candidatas: {notification_summary['candidates']}")
    print(f"Notificaciones por consola: {notification_summary['console']}")
    print(f"Notificaciones Telegram enviadas: {notification_summary['telegram_sent']}")
    print(f"Notificaciones Telegram fallidas: {notification_summary['telegram_failed']}")


def run_worker():
    """Ejecuta el worker una vez o en ciclo segun config.yaml."""
    config = load_config()
    worker_settings = config.get("worker_settings", {})

    if not worker_settings.get("enabled", False):
        print(
            "El worker esta desactivado. "
            "Cambia worker_settings.enabled a true para probar."
        )
        return

    interval_minutes = worker_settings.get("interval_minutes", 5)
    run_once_enabled = worker_settings.get("run_once", True)

    while True:
        try:
            print("Ejecutando worker local de job-watcher...")
            run_once(config)
        except Exception as exc:
            # El worker no debe caer por un fallo puntual de correo o red.
            print(f"Error durante la ejecucion del worker: {exc}")

        if run_once_enabled:
            return

        print(f"Proxima ejecucion en {interval_minutes} minutos.")
        time.sleep(int(interval_minutes) * 60)
        config = load_config()
        worker_settings = config.get("worker_settings", {})
        interval_minutes = worker_settings.get("interval_minutes", interval_minutes)


if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        print("Worker detenido manualmente.")
