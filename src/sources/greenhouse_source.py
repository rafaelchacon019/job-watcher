"""Fuente publica para ofertas alojadas en Greenhouse.

Usa el endpoint publico de job boards de Greenhouse. No hace scraping HTML,
no aplica a ofertas y no guarda resultados.
"""

import requests
import unicodedata

from src.sources.base_source import normalize_job, trim_description


GREENHOUSE_API_URL = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"


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


def _normalize_greenhouse_job(job_data, company):
    """Convierte un registro de Greenhouse al formato comun."""
    location = (job_data.get("location") or {}).get("name", "")
    description = trim_description(job_data.get("content", ""))
    text_for_modality = f"{job_data.get('title', '')} {location} {description}"

    return normalize_job(
        title=job_data.get("title", ""),
        company=company,
        portal="Greenhouse",
        location=location,
        modality=_detect_modality(text_for_modality),
        description=description,
        link=job_data.get("absolute_url", ""),
        source_type="ats_greenhouse",
    )


def fetch_greenhouse_company_jobs(company, timeout=10):
    """Consulta ofertas publicas de una empresa en Greenhouse."""
    company_key = str(company or "").strip()
    if not company_key:
        return []

    url = GREENHOUSE_API_URL.format(company=company_key)

    try:
        response = requests.get(
            url,
            params={"content": "true"},
            timeout=timeout,
            headers={"User-Agent": "job-watcher/1.0"},
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    jobs = data.get("jobs", [])
    return [_normalize_greenhouse_job(job_data, company_key) for job_data in jobs]


def fetch_greenhouse_jobs(companies, timeout=10):
    """Consulta varias empresas Greenhouse configuradas."""
    all_jobs = []

    for company in companies or []:
        all_jobs.extend(fetch_greenhouse_company_jobs(company, timeout=timeout))

    return all_jobs
