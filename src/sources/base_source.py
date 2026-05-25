"""Formato comun para ofertas provenientes de fuentes externas."""

from copy import deepcopy


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


def job_search_text(job):
    """Une titulo, descripcion, ubicacion y otros campos para filtros ATS."""
    return " ".join(
        [
            job.get("title", ""),
            job.get("company", ""),
            job.get("portal", ""),
            job.get("location", ""),
            job.get("modality", ""),
            job.get("description", ""),
            job.get("link", ""),
        ]
    ).lower()


def job_matches_keywords(job, keywords):
    """Revisa si una oferta contiene alguna palabra clave configurada."""
    if not keywords:
        return True

    text = job_search_text(job)
    return any(str(keyword).lower() in text for keyword in keywords)


def filter_jobs_by_keywords(jobs, keywords):
    """Filtra ofertas ATS usando keywords opcionales."""
    return [job for job in jobs if job_matches_keywords(job, keywords)]


def job_has_excluded_keyword(job, exclude_keywords):
    """Detecta palabras de areas no objetivo para esta prueba manual."""
    text = job_search_text(job)
    return any(str(keyword).lower() in text for keyword in exclude_keywords)


def filter_jobs_by_exclusions(jobs, exclude_keywords):
    """Quita ofertas ATS que contienen palabras no objetivo."""
    if not exclude_keywords:
        return jobs, 0

    filtered_jobs = [
        job for job in jobs if not job_has_excluded_keyword(job, exclude_keywords)
    ]
    excluded_count = len(jobs) - len(filtered_jobs)
    return filtered_jobs, excluded_count


def build_ats_scoring_config(config, settings):
    """Agrega preferencias ATS al config usado por calculate_score."""
    scoring_config = deepcopy(config)
    preferred_locations = settings.get("preferred_locations", [])
    configured_locations = scoring_config.get("ubicaciones_preferidas", [])

    for location in preferred_locations:
        if location not in configured_locations:
            configured_locations.append(location)

    scoring_config["ubicaciones_preferidas"] = configured_locations
    return scoring_config


def get_int_setting(settings, key, default):
    """Lee un entero desde config con fallback sencillo."""
    try:
        return int(settings.get(key, default))
    except (TypeError, ValueError):
        return default
