"""Notificaciones locales por consola para ofertas guardadas."""


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

        if email_type == "application_update" and not include_application_updates:
            continue
        if email_type != "job_alert" and not include_application_updates:
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
