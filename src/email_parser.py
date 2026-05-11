"""Parser inicial para convertir correos en posibles ofertas laborales.

Este modulo usa reglas simples y conservadoras. No hace requests a links, no
guarda en SQLite y no calcula puntajes.
"""

import re
import unicodedata
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup


def _repair_text(text):
    """Limpia artefactos comunes antes de usar texto del correo."""
    repaired = str(text or "")

    if any(marker in repaired for marker in ("Ã", "Â", "â")):
        try:
            candidate = repaired.encode("latin-1", errors="ignore").decode(
                "utf-8",
                errors="replace",
            )
            if candidate.count("\ufffd") <= repaired.count("\ufffd"):
                repaired = candidate
        except UnicodeError:
            pass

    return repaired.replace("\ufffd", "").replace("\x00", "")


def _normalize(text):
    """Normaliza texto para comparaciones simples."""
    normalized = unicodedata.normalize("NFD", _repair_text(text).lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _compact_spaces(text):
    """Reduce espacios repetidos para dejar texto mas legible."""
    return re.sub(r"\s+", " ", _repair_text(text)).strip()


def clean_html(html):
    """Convierte HTML en texto legible."""
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return _compact_spaces(soup.get_text(" ", strip=True))


def extract_links_from_html(html):
    """Extrae links unicos desde etiquetas a sin visitar ninguna URL."""
    soup = BeautifulSoup(html or "", "html.parser")
    links = []
    seen = set()

    for tag in soup.find_all("a", href=True):
        link = tag.get("href", "").strip()
        lowered = link.lower()

        if not link or lowered.startswith(("mailto:", "tel:")) or link.startswith("#"):
            continue

        if link not in seen:
            links.append(link)
            seen.add(link)

    return links


def classify_email(subject, sender, text):
    """Clasifica el correo segun asunto, remitente y texto visible."""
    normalized = _normalize(f"{subject} {sender} {text}")

    application_keywords = [
        "candidatura avanza",
        "proceso de seleccion",
        "se comunico contigo",
        "han visto tu cv",
        "vieron tu cv",
        "postulacion",
    ]
    generic_keywords = [
        "newsletter",
        "promocion",
        "publicidad",
    ]
    job_keywords = [
        "vacante",
        "vacantes",
        "empleo",
        "empleos",
        "job alert",
        "nuevas ofertas",
        "postulate",
        "postlate",
        "engineer",
        "developer",
        "desarrollador",
        "analista programador",
    ]

    if any(keyword in normalized for keyword in application_keywords):
        return "application_update"
    if any(keyword in normalized for keyword in generic_keywords):
        return "generic_notification"
    if any(keyword in normalized for keyword in job_keywords):
        return "job_alert"

    return "unknown"


def detect_portal(sender, subject):
    """Detecta el portal de empleo usando remitente y asunto."""
    text = _normalize(f"{sender} {subject}")

    if "linkedin" in text:
        return "LinkedIn"
    if "computrabajo" in text:
        return "Computrabajo"
    if "elempleo" in text or "el empleo" in text:
        return "El Empleo"
    if "torre" in text:
        return "Torre"
    if "magneto" in text:
        return "Magneto"

    return "Desconocido"


def _is_generic_alert_subject(subject):
    """Detecta asuntos que son alertas generales y no una vacante concreta."""
    normalized = _normalize(subject)
    phrases = [
        "tienes nuevas ofertas de empleo",
        "nuevas ofertas de empleo",
        "ofertas de empleo esperandote",
        "nuevas vacantes listas",
        "estas empresas necesitan talento",
        "tu proximo paso",
        "te buscan",
        "te buscan para nuevos empleos",
    ]
    return any(phrase in normalized for phrase in phrases)


def _is_generic_title(title):
    """Detecta titulos temporales que conviene reemplazar si hay mejor dato."""
    normalized = _normalize(title)
    phrases = [
        "alerta general de empleo",
        "nuevas vacantes",
        "nuevas ofertas",
        "buscas empleo como",
        "te buscan",
        "empresas necesitan talento",
    ]
    return any(phrase in normalized for phrase in phrases)


def guess_title_from_subject(subject):
    """Intenta usar el asunto como titulo temporal de la oferta."""
    cleaned = _compact_spaces(subject)
    normalized = _normalize(cleaned)

    if not cleaned:
        return "No detectado"

    if classify_email(cleaned, "", "") == "application_update":
        return "Seguimiento de postulación"

    if _is_generic_alert_subject(cleaned):
        return "Alerta general de empleo"

    cleaned = re.sub(
        r"(?i)^(nueva oferta|job alert|alerta de empleo|empleo|trabajo)\s*[:\-]\s*",
        "",
        cleaned,
    ).strip()

    match = re.search(r"\s+en\s+.+$", cleaned, flags=re.IGNORECASE)
    if match:
        return cleaned[: match.start()].strip(" -|") or cleaned

    if normalized.startswith("postulate ") or normalized.startswith("postlate "):
        return cleaned

    return cleaned


def guess_company_from_subject(subject):
    """Intenta extraer empresa cuando el asunto contiene 'en Empresa'."""
    cleaned = _compact_spaces(subject)
    match = re.search(r"\s+en\s+(.+)$", cleaned, flags=re.IGNORECASE)
    if not match:
        return "No detectada"

    company = match.group(1)
    company = re.split(r"\s[-|]\s|,", company, maxsplit=1)[0]
    return _compact_spaces(company) or "No detectada"


def guess_modality(text):
    """Detecta modalidad usando palabras comunes."""
    normalized = _normalize(text)

    if "remoto" in normalized or "remote" in normalized:
        return "Remoto"
    if "hibrido" in normalized or "hybrid" in normalized:
        return "Híbrido"
    if "presencial" in normalized:
        return "Presencial"

    return "No detectada"


def guess_location(text):
    """Detecta ubicacion con una lista corta de ciudades y pais."""
    normalized = _normalize(text)
    locations = [
        ("bogota", "Bogotá"),
        ("medellin", "Medellín"),
        ("cali", "Cali"),
        ("barranquilla", "Barranquilla"),
        ("colombia", "Colombia"),
        ("remoto", "Remoto"),
        ("remote", "Remoto"),
    ]

    for keyword, label in locations:
        if keyword in normalized:
            return label

    return "No detectada"


def extract_job_info_from_link(link):
    """Extrae datos simples desde un link sin hacer requests."""
    decoded_link = unquote(str(link or ""))
    normalized_link = _normalize(decoded_link)
    info = {
        "title": None,
        "location": None,
    }

    match = re.search(
        r"oferta-de-trabajo-de-([a-z0-9-]+?)-en-([a-z0-9-]+)",
        normalized_link,
    )
    if match:
        raw_title = match.group(1)
        title_words = [
            word.capitalize()
            for word in raw_title.split("-")
            if word and word not in {"a", "de", "del", "la", "el"}
        ]
        if title_words:
            info["title"] = " ".join(title_words)

        raw_location = match.group(2)
        info["location"] = guess_location(raw_location.replace("-", " "))

    if not info["location"]:
        info["location"] = guess_location(normalized_link.replace("-", " "))

    return info


def _is_home_link(link):
    """Detecta links que parecen llevar al home de un portal."""
    parsed = urlparse(link)
    path = parsed.path.strip("/")
    return bool(parsed.netloc) and not path and not parsed.query


def _clean_links(links):
    """Quita links vacios, repetidos o claramente poco utiles."""
    ignored_tokens = [
        "logo",
        "home",
        "header",
        "footer",
        "supportcenter.computrabajo.com",
        "/hc/",
        "support",
        "centro-de-ayuda",
        "ayuda",
        "unsubscribe",
        "privacy",
        "settings",
        "feed",
        "email_logo",
        "email-logo",
        "play.google.com",
        "itunes.apple.com",
        "apps.apple.com",
        "app store",
        "preferencias",
        "tracking",
        "track",
        "beacon",
        "pixel",
    ]
    cleaned_links = []
    seen = set()

    for link in links:
        clean_link = str(link or "").strip()
        lowered = clean_link.lower()

        if not clean_link or lowered.startswith(("mailto:", "tel:")):
            continue
        if clean_link.startswith("#") or _is_home_link(clean_link):
            continue
        if any(token in lowered for token in ignored_tokens):
            continue
        if clean_link not in seen:
            cleaned_links.append(clean_link)
            seen.add(clean_link)

    return cleaned_links


def select_best_job_link(links, portal):
    """Selecciona el link mas util sin visitar ninguna URL."""
    useful_tokens = [
        "linkedin.com/jobs",
        "jobs",
        "job",
        "empleo",
        "empleos",
        "ofertas-de-trabajo",
        "vacante",
        "candidate",
        "candidato",
        "oferta",
        "computrabajo",
        "elempleo",
    ]
    portal_tokens = {
        "LinkedIn": ["linkedin.com/jobs", "linkedin.com/comm/jobs"],
        "Computrabajo": ["computrabajo"],
        "El Empleo": ["elempleo", "eltiempo.com/empleos"],
        "Torre": ["torre"],
        "Magneto": ["magneto"],
    }
    cleaned_links = _clean_links(links)

    for token in portal_tokens.get(portal, []):
        for link in cleaned_links:
            if token in link.lower():
                return link

    for link in cleaned_links:
        lowered = link.lower()
        if any(token in lowered for token in useful_tokens):
            return link

    return cleaned_links[0] if cleaned_links else ""


def parse_email_to_jobs(email_data):
    """Convierte un correo completo en una posible oferta laboral."""
    subject = _compact_spaces(email_data.get("subject", ""))
    sender = _compact_spaces(email_data.get("sender", ""))
    text_body = _compact_spaces(email_data.get("text_body", ""))
    html_body = email_data.get("html_body", "")
    html_text = clean_html(html_body)
    combined_text = _compact_spaces(f"{subject} {sender} {text_body} {html_text}")

    portal = detect_portal(sender, subject)
    email_type = classify_email(subject, sender, combined_text)
    links = extract_links_from_html(html_body)
    link = select_best_job_link(links, portal)
    link_info = extract_job_info_from_link(link)
    description = combined_text[:500]

    if email_type == "application_update":
        title = "Seguimiento de postulación"
        # En seguimientos el asunto suele describir el estado del proceso, no
        # una empresa confiable. Evitamos guardar fragmentos como empresa.
        company = "No detectada"
    else:
        title = guess_title_from_subject(subject)
        company = guess_company_from_subject(subject)

        if _is_generic_title(title) and link_info.get("title"):
            title = link_info["title"]

    location = guess_location(combined_text)
    if location == "No detectada" and link_info.get("location"):
        location = link_info["location"]

    return [
        {
            "title": title,
            "company": company,
            "portal": portal,
            "location": location,
            "modality": guess_modality(combined_text),
            "description": description,
            "link": link,
            "email_type": email_type,
        }
    ]


def parse_emails_to_jobs(emails):
    """Convierte una lista de correos en una lista de posibles ofertas."""
    jobs = []

    for email_data in emails:
        jobs.extend(parse_email_to_jobs(email_data))

    return jobs
