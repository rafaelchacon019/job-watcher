"""Formato comun para ofertas provenientes de fuentes externas."""

STANDARD_JOB_FIELDS = [
    "title",
    "company",
    "portal",
    "location",
    "modality",
    "description",
    "link",
    "source_type",
    "email_type",
]


def normalize_job(
    title="",
    company="",
    portal="",
    location="",
    modality="",
    description="",
    link="",
    source_type="",
    email_type="job_alert",
):
    """Crea una oferta con el formato estandar del proyecto."""
    return {
        "title": str(title or "").strip() or "No detectado",
        "company": str(company or "").strip() or "No detectada",
        "portal": str(portal or "").strip() or "Desconocido",
        "location": str(location or "").strip() or "No detectada",
        "modality": str(modality or "").strip() or "No detectada",
        "description": str(description or "").strip(),
        "link": str(link or "").strip(),
        "source_type": str(source_type or "").strip() or "ats",
        "email_type": str(email_type or "").strip() or "job_alert",
    }


def trim_description(description, max_length=500):
    """Recorta descripciones largas para mostrar datos manejables."""
    cleaned = " ".join(str(description or "").split())

    if len(cleaned) <= max_length:
        return cleaned

    return cleaned[:max_length].rstrip() + "..."
