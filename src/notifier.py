"""Notificaciones locales para ofertas guardadas."""

import os

import requests


def format_job_notification(job):
    """Crea un texto legible para mostrar una oferta prioritaria."""
    reasons = job.get("reasons", [])[:5]
    reason_lines = "\n".join(f"- {reason}" for reason in reasons)

    if not reason_lines:
        reason_lines = "- Sin motivos registrados"

    return (
        "Nueva oferta prioritaria:\n"
        f"Score: {job.get('score', 0)}\n"
        f"Cargo: {job.get('title', '')}\n"
        f"Empresa: {job.get('company', '')}\n"
        f"Portal: {job.get('portal', '')}\n"
        f"Ubicacion: {job.get('location', '')}\n"
        f"Modalidad: {job.get('modality', '')}\n"
        "Motivos:\n"
        f"{reason_lines}\n"
        f"Link: {job.get('link', '')}"
    )


def get_jobs_for_notification(jobs, settings):
    """Filtra y ordena las ofertas que merecen notificacion."""
    min_score = settings.get("min_score", 20)
    max_notifications = settings.get("max_notifications", 5)
    include_application_updates = settings.get("include_application_updates", False)
    filtered_jobs = []

    for job in jobs:
        email_type = job.get("email_type", "")

        if email_type == "job_alert":
            pass
        elif email_type == "application_update" and include_application_updates:
            pass
        else:
            continue

        if job.get("score", 0) < min_score:
            continue

        filtered_jobs.append(job)

    sorted_jobs = sorted(
        filtered_jobs,
        key=lambda job: job.get("score", 0),
        reverse=True,
    )
    return sorted_jobs[:max_notifications]


def print_job_notifications(jobs):
    """Imprime las notificaciones en consola."""
    if not jobs:
        print("No hay ofertas que superen el puntaje minimo de notificacion.")
        return

    for job in jobs:
        print(format_job_notification(job))
        print()


def load_telegram_credentials():
    """Carga credenciales de Telegram desde .env sin imprimir secretos."""
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Falta instalar python-dotenv. Ejecuta: pip install -r requirements.txt"
        ) from exc

    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        raise ValueError(
            "Falta configurar TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en .env local."
        )

    return {
        "TELEGRAM_BOT_TOKEN": bot_token,
        "TELEGRAM_CHAT_ID": chat_id,
    }


def send_telegram_message(message, credentials):
    """Envia un mensaje por Telegram usando Bot API."""
    bot_token = credentials["TELEGRAM_BOT_TOKEN"]
    chat_id = credentials["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if not response.ok:
            return False

        response_data = response.json()
        return bool(response_data.get("ok"))
    except (requests.RequestException, ValueError):
        return False


def send_telegram_notifications(jobs):
    """Envia una notificacion de Telegram por cada oferta recibida."""
    credentials = load_telegram_credentials()
    summary = {
        "enviados": 0,
        "fallidos": 0,
    }

    for job in jobs:
        message = format_job_notification(job)
        if send_telegram_message(message, credentials):
            summary["enviados"] += 1
        else:
            summary["fallidos"] += 1

    return summary
