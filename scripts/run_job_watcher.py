"""Worker local para ejecutar job-watcher de forma periodica.

Este script no esta conectado a main.py. Lee correos solo si email_settings y
worker_settings estan activos, guarda nuevas ofertas reales y notifica si aplica.
No genera CSV.
"""

import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import init_db, job_exists_by_fingerprint, save_job_if_not_exists
from src.deduplication import build_job_fingerprint
from src.ai_analyzer import analyze_jobs_batch
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
from src.logger import setup_logger
from src.scorer import calculate_score
from src.sources.base_source import (
    build_ats_scoring_config,
    filter_jobs_by_exclusions,
    filter_jobs_by_keywords,
    get_int_setting,
)
from src.sources.greenhouse_source import fetch_greenhouse_jobs
from src.sources.lever_source import fetch_lever_jobs


LOGGER = logging.getLogger("job_watcher.worker")


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
        scored_job = {
            **job,
            "score": score_result["score"],
            "reasons": score_result["reasons"],
        }
        scored_job["fingerprint"] = job.get("fingerprint") or build_job_fingerprint(
            scored_job
        )
        scored_jobs.append(scored_job)

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
        LOGGER.error("No se pudo guardar el checkpoint de correos: %s", exc)
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
        "duplicates_by_fingerprint": 0,
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
        duplicated_fingerprint = job_exists_by_fingerprint(
            job_to_save.get("fingerprint", ""),
            job_to_save.get("link", ""),
        )

        if save_job_if_not_exists(job_to_save):
            summary["new_jobs"].append(job_to_save)
        else:
            summary["duplicates"] += 1
            if duplicated_fingerprint:
                summary["duplicates_by_fingerprint"] += 1

    return summary


def empty_save_summary():
    """Crea un resumen vacio de guardado."""
    return {
        "new_jobs": [],
        "duplicates": 0,
        "duplicates_by_fingerprint": 0,
        "ignored": 0,
    }


def process_email_sources(config):
    """Procesa correos configurados y guarda ofertas nuevas."""
    email_settings = config.get("email_settings", {})
    checkpoint_settings = config.get("checkpoint_settings", {})

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

    return {
        "correos_leidos": len(emails),
        "correos_nuevos": len(emails_to_process),
        "checkpoint_ignorados": checkpoint_summary["ignored"],
        "ofertas_parseadas": len(jobs),
        "checkpoint_actualizado": checkpoint_updated,
        "save_summary": save_summary,
    }


def empty_email_summary():
    """Crea un resumen vacio de correo cuando IMAP esta desactivado."""
    return {
        "correos_leidos": 0,
        "correos_nuevos": 0,
        "checkpoint_ignorados": 0,
        "ofertas_parseadas": 0,
        "checkpoint_actualizado": False,
        "save_summary": empty_save_summary(),
    }


def process_ats_sources(config):
    """Consulta fuentes ATS, filtra, puntua y guarda ofertas nuevas."""
    settings = config.get("ats_sources", {})
    summary = {
        "ats_total": 0,
        "ats_filtradas_keywords": 0,
        "ats_excluidas": 0,
        "ats_score_suficiente": 0,
        "save_summary": empty_save_summary(),
    }

    if not settings.get("enabled", False):
        return summary

    greenhouse_companies = settings.get("greenhouse_companies", [])
    lever_companies = settings.get("lever_companies", [])
    keywords = settings.get("keywords", [])
    exclude_keywords = settings.get("exclude_keywords", [])
    min_score = get_int_setting(settings, "min_score", 20)
    scoring_config = build_ats_scoring_config(config, settings)

    jobs = []
    jobs.extend(fetch_greenhouse_jobs(greenhouse_companies))
    jobs.extend(fetch_lever_jobs(lever_companies))

    keyword_jobs = filter_jobs_by_keywords(jobs, keywords)
    target_jobs, excluded_count = filter_jobs_by_exclusions(
        keyword_jobs,
        exclude_keywords,
    )
    scored_jobs = score_jobs(target_jobs, scoring_config)
    enough_score_jobs = [
        job for job in scored_jobs if job.get("score", 0) >= min_score
    ]
    save_summary = save_new_jobs(enough_score_jobs)

    summary.update(
        {
            "ats_total": len(jobs),
            "ats_filtradas_keywords": len(keyword_jobs),
            "ats_excluidas": excluded_count,
            "ats_score_suficiente": len(enough_score_jobs),
            "save_summary": save_summary,
        }
    )
    return summary


def attach_ai_analysis_for_telegram(jobs_to_notify, config, telegram_enabled):
    """Agrega analisis IA solo a ofertas nuevas que se enviaran por Telegram."""
    ai_settings = config.get("ai_settings", {})

    if not telegram_enabled:
        return 0

    if not ai_settings.get("enabled", False):
        return 0

    if not ai_settings.get("use_in_telegram", False):
        return 0

    if not jobs_to_notify:
        return 0

    try:
        results = analyze_jobs_batch(jobs_to_notify, config)
    except Exception as exc:
        # La IA es opcional: si falla, Telegram se envia con el formato normal.
        LOGGER.warning("No se pudo agregar analisis IA a Telegram: %s", exc)
        return 0

    for result in results:
        result["job"]["ai_analysis"] = result.get("analysis", {})

    return len(results)


def notify_new_jobs(new_jobs, notification_settings, config):
    """Notifica ofertas nuevas segun configuracion de canales."""
    summary = {
        "candidates": 0,
        "console": 0,
        "ai_analyzed": 0,
        "telegram_sent": 0,
        "telegram_failed": 0,
    }

    if not notification_settings.get("enabled", False):
        LOGGER.info("Notificaciones desactivadas en notification_settings.enabled.")
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
        summary["ai_analyzed"] = attach_ai_analysis_for_telegram(
            jobs_to_notify,
            config,
            telegram_enabled,
        )
        try:
            telegram_summary = send_telegram_notifications(jobs_to_notify)
            summary["telegram_sent"] = telegram_summary["enviados"]
            summary["telegram_failed"] = telegram_summary["fallidos"]
        except ValueError as exc:
            LOGGER.warning("Telegram no configurado: %s", exc)
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
        LOGGER.warning("Intervalo invalido. Se usaran 5 minutos por defecto.")
        return default_interval

    if interval_minutes <= 0:
        LOGGER.warning("Intervalo menor o igual a 0. Se usaran 5 minutos por defecto.")
        return default_interval

    return interval_minutes


def print_next_run(interval_minutes):
    """Muestra la hora aproximada de la siguiente ejecucion."""
    next_run_at = datetime.now() + timedelta(minutes=interval_minutes)
    LOGGER.info("Proxima ejecucion: %s", next_run_at.strftime("%Y-%m-%d %H:%M:%S"))


def run_once(config):
    """Ejecuta una pasada completa del worker."""
    email_settings = config.get("email_settings", {})
    ats_settings = config.get("ats_sources", {})
    notification_settings = config.get("notification_settings", {})
    email_enabled = email_settings.get("enabled", False)
    ats_enabled = ats_settings.get("enabled", False)

    if not email_enabled and not ats_enabled:
        LOGGER.info(
            "Correo y ATS estan desactivados. "
            "Activa email_settings.enabled o ats_sources.enabled para procesar."
        )
        return

    init_db()

    if email_enabled:
        try:
            email_summary = process_email_sources(config)
        except Exception as exc:
            LOGGER.exception("Error procesando correos: %s", exc)
            email_summary = empty_email_summary()
    else:
        LOGGER.info("La lectura de correos esta desactivada en email_settings.enabled.")
        email_summary = empty_email_summary()

    try:
        ats_summary = process_ats_sources(config)
    except Exception as exc:
        LOGGER.exception("Error procesando fuentes ATS: %s", exc)
        ats_summary = {
            "ats_total": 0,
            "ats_filtradas_keywords": 0,
            "ats_excluidas": 0,
            "ats_score_suficiente": 0,
            "save_summary": empty_save_summary(),
        }
    email_save_summary = email_summary["save_summary"]
    ats_save_summary = ats_summary["save_summary"]
    new_jobs_to_notify = (
        email_save_summary["new_jobs"] + ats_save_summary["new_jobs"]
    )
    notification_summary = notify_new_jobs(
        new_jobs_to_notify,
        notification_settings,
        config,
    )

    LOGGER.info(
        "Resumen del ciclo | correos_leidos=%s | correos_nuevos=%s | "
        "checkpoint_ignorados=%s | ofertas_parseadas=%s | nuevas_guardadas=%s | "
        "duplicadas=%s | ignoradas=%s | checkpoint_actualizado=%s | "
        "ats_total=%s | ats_filtradas_keywords=%s | ats_excluidas=%s | "
        "ats_score_suficiente=%s | ats_nuevas_guardadas=%s | ats_duplicadas=%s | "
        "duplicadas_por_fingerprint=%s | ats_duplicadas_por_fingerprint=%s | "
        "notificaciones_candidatas=%s | consola=%s | ia_analizadas=%s | telegram_enviadas=%s | "
        "telegram_fallidas=%s",
        email_summary["correos_leidos"],
        email_summary["correos_nuevos"],
        email_summary["checkpoint_ignorados"],
        email_summary["ofertas_parseadas"],
        len(email_save_summary["new_jobs"]),
        email_save_summary["duplicates"],
        email_save_summary["ignored"],
        "si" if email_summary["checkpoint_actualizado"] else "no",
        ats_summary["ats_total"],
        ats_summary["ats_filtradas_keywords"],
        ats_summary["ats_excluidas"],
        ats_summary["ats_score_suficiente"],
        len(ats_save_summary["new_jobs"]),
        ats_save_summary["duplicates"],
        email_save_summary["duplicates_by_fingerprint"],
        ats_save_summary["duplicates_by_fingerprint"],
        notification_summary["candidates"],
        notification_summary["console"],
        notification_summary["ai_analyzed"],
        notification_summary["telegram_sent"],
        notification_summary["telegram_failed"],
    )


def run_worker():
    """Ejecuta el worker una vez o en ciclo segun config.yaml."""
    config = load_config()
    setup_logger(config.get("logging_settings", {}))
    worker_settings = config.get("worker_settings", {})
    LOGGER.info("Worker local iniciado.")

    if not worker_settings.get("enabled", False):
        LOGGER.info(
            "El worker esta desactivado. "
            "Cambia worker_settings.enabled a true para probar."
        )
        return

    interval_minutes = get_interval_minutes(worker_settings)
    run_once_enabled = worker_settings.get("run_once", True)

    while True:
        try:
            LOGGER.info("Iniciando ciclo del worker: %s", current_time_label())
            run_once(config)
        except Exception as exc:
            # El worker no debe caer por un fallo puntual de correo o red.
            LOGGER.exception("Error durante la ejecucion del worker: %s", exc)

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
            LOGGER.exception("No se pudo recargar config.yaml: %s", exc)


if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        if LOGGER.handlers:
            LOGGER.info("Worker detenido manualmente.")
        else:
            print("Worker detenido manualmente.")
