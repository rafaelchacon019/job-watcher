"""Worker local para ejecutar job-watcher de forma periodica.

Este script no esta conectado a main.py. Lee correos solo si email_settings y
worker_settings estan activos, guarda nuevas ofertas reales y notifica si aplica.
No genera CSV.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import init_db, save_job_if_not_exists
from src.email_checkpoint import (
    filter_unprocessed_emails,
    load_checkpoint,
    save_checkpoint,
    update_checkpoint,
)
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


def load_email_checkpoint(checkpoint_settings):
    """Carga el checkpoint si esta activo."""
    if not checkpoint_settings.get("enabled", True):
        return None

    return load_checkpoint(checkpoint_settings.get("path"))


def get_emails_to_process(emails, checkpoint, checkpoint_settings):
    """Filtra correos ya procesados usando el checkpoint local."""
    summary = {
        "enabled": checkpoint_settings.get("enabled", True),
        "ignored": 0,
    }

    if not summary["enabled"]:
        return emails, summary

    new_emails = filter_unprocessed_emails(emails, checkpoint)
    summary["ignored"] = len(emails) - len(new_emails)

    return new_emails, summary


def update_email_checkpoint(checkpoint, processed_emails, checkpoint_settings):
    """Actualiza el checkpoint sin detener el worker si hay un fallo local."""
    if not checkpoint_settings.get("enabled", True):
        return False

    try:
        updated_checkpoint = update_checkpoint(
            checkpoint or {},
            processed_emails,
            checkpoint_settings.get("max_processed_ids", 500),
        )
        save_checkpoint(updated_checkpoint, checkpoint_settings.get("path"))
        return True
    except OSError as exc:
        print(f"No se pudo guardar el checkpoint de correos: {exc}")
        return False


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


def current_time_label():
    """Devuelve la hora local en formato legible para consola."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_interval_minutes(worker_settings):
    """Obtiene un intervalo valido para el modo continuo."""
    default_interval = 5

    try:
        interval_minutes = int(worker_settings.get("interval_minutes", default_interval))
    except (TypeError, ValueError):
        print("Intervalo invalido. Se usaran 5 minutos por defecto.")
        return default_interval

    if interval_minutes <= 0:
        print("Intervalo menor o igual a 0. Se usaran 5 minutos por defecto.")
        return default_interval

    return interval_minutes


def print_next_run(interval_minutes):
    """Muestra la hora aproximada de la siguiente ejecucion."""
    next_run_at = datetime.now() + timedelta(minutes=interval_minutes)
    print(f"Proxima ejecucion: {next_run_at.strftime('%Y-%m-%d %H:%M:%S')}")


def run_once(config):
    """Ejecuta una pasada completa del worker."""
    email_settings = config.get("email_settings", {})
    notification_settings = config.get("notification_settings", {})
    checkpoint_settings = config.get("checkpoint_settings", {})

    if not email_settings.get("enabled", False):
        print("La lectura de correos esta desactivada en email_settings.enabled.")
        return

    init_db()

    checkpoint = load_email_checkpoint(checkpoint_settings)
    emails = read_recent_filtered_emails(email_settings)
    emails_to_process, checkpoint_summary = get_emails_to_process(
        emails,
        checkpoint,
        checkpoint_settings,
    )
    jobs = parse_emails_to_jobs(emails_to_process)
    scored_jobs = score_jobs(jobs, config)
    save_summary = save_new_jobs(scored_jobs)
    checkpoint_updated = update_email_checkpoint(
        checkpoint,
        emails_to_process,
        checkpoint_settings,
    )
    notification_summary = notify_new_jobs(
        save_summary["new_jobs"],
        notification_settings,
    )

    print(f"Correos leidos: {len(emails)}")
    print(f"Correos nuevos para procesar: {len(emails_to_process)}")
    print(f"Correos ignorados por checkpoint: {checkpoint_summary['ignored']}")
    print(f"Ofertas parseadas: {len(jobs)}")
    print(f"Ofertas nuevas guardadas: {len(save_summary['new_jobs'])}")
    print(f"Duplicadas ignoradas: {save_summary['duplicates']}")
    print(f"Ofertas ignoradas por filtros: {save_summary['ignored']}")
    print(f"Checkpoint actualizado: {'si' if checkpoint_updated else 'no'}")
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

    interval_minutes = get_interval_minutes(worker_settings)
    run_once_enabled = worker_settings.get("run_once", True)

    while True:
        try:
            print(f"Iniciando ciclo del worker: {current_time_label()}")
            run_once(config)
        except Exception as exc:
            # El worker no debe caer por un fallo puntual de correo o red.
            print(f"Error durante la ejecucion del worker: {exc}")

        if run_once_enabled:
            return

        print_next_run(interval_minutes)
        time.sleep(interval_minutes * 60)

        try:
            config = load_config()
            worker_settings = config.get("worker_settings", {})
            interval_minutes = get_interval_minutes(worker_settings)
            run_once_enabled = worker_settings.get("run_once", run_once_enabled)
        except Exception as exc:
            print(f"No se pudo recargar config.yaml: {exc}")


if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        print("Worker detenido manualmente.")
