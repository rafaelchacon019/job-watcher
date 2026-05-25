"""Utilidades para detectar ofertas similares entre fuentes."""

import re
import unicodedata
from difflib import SequenceMatcher


STOPWORDS = {
    "a",
    "an",
    "and",
    "de",
    "del",
    "el",
    "en",
    "for",
    "la",
    "of",
    "para",
    "the",
    "y",
}

EMPTY_VALUES = {
    "",
    "no detectada",
    "no detectado",
    "desconocido",
    "unknown",
    "n/a",
}


def normalize_text(value):
    """Normaliza texto para comparaciones entre fuentes distintas."""
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-z0-9+#.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _slug(value):
    """Convierte texto normalizado en una pieza estable para fingerprint."""
    normalized = normalize_text(value)
    return re.sub(r"[^a-z0-9+#.]+", "-", normalized).strip("-")


def normalize_title(title):
    """Normaliza titulos quitando ruido comun de ofertas."""
    normalized = normalize_text(title)
    noise_patterns = [
        r"\bremote\b",
        r"\bremoto\b",
        r"\bhybrid\b",
        r"\bhibrido\b",
        r"\bbogota\b",
        r"\bcolombia\b",
        r"\blatam\b",
        r"\bjunior\b",
        r"\bsenior\b",
        r"\bsemi senior\b",
    ]

    for pattern in noise_patterns:
        normalized = re.sub(pattern, " ", normalized)

    return re.sub(r"\s+", " ", normalized).strip()


def normalize_company(company):
    """Normaliza empresa y evita usar valores no detectados."""
    normalized = normalize_text(company)

    if normalized in EMPTY_VALUES:
        return ""

    normalized = re.sub(r"\b(inc|llc|ltd|corp|company|co)\b", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_location(location):
    """Normaliza ubicacion con valores utiles para comparar."""
    normalized = normalize_text(location)

    if normalized in EMPTY_VALUES:
        return ""

    if "remote" in normalized or "remoto" in normalized:
        return "remote"
    if "bogota" in normalized:
        return "bogota"
    if "colombia" in normalized:
        return "colombia"

    return normalized


def _role_keywords(job):
    """Extrae palabras clave del cargo desde titulo y descripcion."""
    text = normalize_text(f"{job.get('title', '')} {job.get('description', '')}")
    words = []

    for word in text.split():
        if len(word) < 3 or word in STOPWORDS:
            continue
        if word not in words:
            words.append(word)
        if len(words) >= 6:
            break

    return "-".join(words)


def build_job_fingerprint(job):
    """Construye una huella estable para detectar duplicados probables."""
    title = _slug(normalize_title(job.get("title", "")))
    company = _slug(normalize_company(job.get("company", "")))
    location = _slug(_normalize_location(job.get("location", "")))
    role_keywords = _role_keywords(job)

    parts = [
        title or role_keywords,
        company or "empresa-no-detectada",
        location or "ubicacion-no-detectada",
        role_keywords,
    ]
    return "|".join(part for part in parts if part)


def are_jobs_similar(job_a, job_b):
    """Compara dos ofertas para detectar similitud probable."""
    fingerprint_a = job_a.get("fingerprint") or build_job_fingerprint(job_a)
    fingerprint_b = job_b.get("fingerprint") or build_job_fingerprint(job_b)

    if fingerprint_a and fingerprint_a == fingerprint_b:
        return True

    title_a = normalize_title(job_a.get("title", ""))
    title_b = normalize_title(job_b.get("title", ""))
    company_a = normalize_company(job_a.get("company", ""))
    company_b = normalize_company(job_b.get("company", ""))
    location_a = _normalize_location(job_a.get("location", ""))
    location_b = _normalize_location(job_b.get("location", ""))

    titles_are_close = SequenceMatcher(None, title_a, title_b).ratio() >= 0.86
    companies_match = bool(company_a and company_b and company_a == company_b)
    locations_match = not location_a or not location_b or location_a == location_b

    return titles_are_close and companies_match and locations_match
