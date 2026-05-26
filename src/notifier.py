"""Notificaciones locales para ofertas guardadas."""

import os
import unicodedata

import requests

from src.email_parser import is_generic_or_promotional_title


def _normalize(text):
    """Normaliza texto para filtros simples de notificacion."""
    normalized = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _contains(text, phrase):
    """Busca una frase normalizada dentro de otro texto."""
    return _normalize(phrase) in _normalize(text)


def _has_junior_signal(text):
    """Detecta senales basicas de nivel junior o inicial."""
    junior_patterns = [
        "junior",
        "entry level",
        "trainee",
        "aprendiz",
        "practicante",
    ]
    return any(_contains(text, pattern) for pattern in junior_patterns)


def _is_non_target_area(job):
    """Detecta areas que no son prioridad para notificaciones."""
    text = " ".join(
        [
            job.get("title", ""),
            job.get("description", ""),
            job.get("link", ""),
        ]
    )
    non_target_patterns = [
        "AI/ML",
        "Machine Learning",
        "Data Scientist",
        "Data Engineer",
        "Data Analyst",
        "DevOps",
        "Cloud Engineer",
        "Cybersecurity",
        "Security Engineer",
    ]

    if any(_contains(text, pattern) for pattern in non_target_patterns):
        return True

    if _contains(text, "QA Automation") and not _has_junior_signal(text):
        return True

    return False


def format_job_notification(job):
    """Crea un texto legible para mostrar una oferta prioritaria."""
    reasons = job.get("reasons", [])[:5]
    reason_lines = "\n".join(f"- {reason}" for reason in reasons)
    ai_section = _format_ai_analysis(job.get("ai_analysis"))

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
        f"{ai_section}"
        f"Link: {job.get('link', '')}"
    )


def _format_ai_analysis(analysis):
    """Formatea un resumen IA compacto si la oferta lo trae."""
    if not analysis:
        return ""

    stack = ", ".join(analysis.get("detected_stack", [])[:5])
    red_flags = ", ".join(analysis.get("red_flags", [])[:3])

    return (
        "Analisis IA:\n"
        f"- Compatibilidad: {analysis.get('match_level', 'No detectada')}\n"
        f"- Seniority estimado: {analysis.get('estimated_seniority', 'No detectado')}\n"
        f"- Stack detectado: {stack or 'No detectado'}\n"
        f"- Riesgos: {red_flags or 'Sin riesgos detectados'}\n"
        f"- Recomendacion: {analysis.get('recommendation', 'Revisar manualmente')}\n"
    )


def get_jobs_for_notification(jobs, settings):
    """Filtra y ordena las ofertas que merecen notificacion."""
    min_score = settings.get("strict_min_score", settings.get("min_score", 20))
    max_notifications = settings.get("max_notifications", 5)
    skip_generic_titles = settings.get("skip_generic_titles", True)
    skip_non_target_areas = settings.get("skip_non_target_areas", True)
    filtered_jobs = []

    for job in jobs:
        if job.get("email_type", "") != "job_alert":
            continue

        if job.get("score", 0) < min_score:
            continue

        if skip_generic_titles and is_generic_or_promotional_title(job.get("title", "")):
            continue

        if skip_non_target_areas and _is_non_target_area(job):
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
