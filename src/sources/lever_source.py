"""Fuente publica para ofertas alojadas en Lever.

Usa el endpoint publico de postings de Lever. No hace scraping HTML, no aplica
a ofertas y no guarda resultados.
"""

import requests
import unicodedata

from src.sources.base_source import normalize_job, trim_description


LEVER_API_URL = "https://api.lever.co/v0/postings/{company}"


def _detect_modality(text):
    """Detecta modalidad con reglas simples sobre texto publico."""
    normalized = unicodedata.normalize("NFD", str(text or "").lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )

    if "remote" in normalized or "remoto" in normalized:
        return "Remoto"
    if "hybrid" in normalized or "hibrido" in normalized:
        return "Hibrido"
    if "onsite" in normalized or "presencial" in normalized:
        return "Presencial"

    return "No detectada"


def _normalize_lever_job(job_data, company):
    """Convierte un registro de Lever al formato comun."""
    categories = job_data.get("categories") or {}
    location = categories.get("location", "")
    workplace_type = job_data.get("workplaceType", "")
    description = trim_description(
        job_data.get("descriptionPlain") or job_data.get("description", "")
    )
    text_for_modality = (
        f"{job_data.get('text', '')} {location} {workplace_type} {description}"
    )

    return normalize_job(
        title=job_data.get("text", ""),
        company=company,
        portal="Lever",
        location=location,
        modality=_detect_modality(text_for_modality),
        description=description,
        link=job_data.get("hostedUrl") or job_data.get("applyUrl", ""),
        source_type="ats_lever",
    )


def fetch_lever_company_jobs(company, timeout=10):
    """Consulta ofertas publicas de una empresa en Lever."""
    company_key = str(company or "").strip()
    if not company_key:
        return []

    url = LEVER_API_URL.format(company=company_key)

    try:
        response = requests.get(
            url,
            params={"mode": "json"},
            timeout=timeout,
            headers={"User-Agent": "job-watcher/1.0"},
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    return [_normalize_lever_job(job_data, company_key) for job_data in data]


def fetch_lever_jobs(companies, timeout=10):
    """Consulta varias empresas Lever configuradas."""
    all_jobs = []

    for company in companies or []:
        all_jobs.extend(fetch_lever_company_jobs(company, timeout=timeout))

    return all_jobs
