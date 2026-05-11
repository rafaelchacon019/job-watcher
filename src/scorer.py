"""Motor simple de puntaje para ofertas laborales."""

import re
import unicodedata


def _normalize(text):
    """Convierte texto a minusculas y sin tildes para comparar mejor."""
    text = str(text or "").lower()
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _job_text(job):
    """Une los campos principales que se usan para buscar coincidencias."""
    fields = [
        job.get("title", ""),
        job.get("company", ""),
        job.get("portal", ""),
        job.get("description", ""),
        job.get("location", ""),
        job.get("modality", ""),
        job.get("link", ""),
    ]
    return " ".join(fields)


def _contains_keyword(text, keyword):
    """Busca una palabra o frase evitando falsos positivos en palabras simples."""
    normalized_text = _normalize(text)
    normalized_keyword = _normalize(keyword)

    if not normalized_keyword:
        return False

    if re.fullmatch(r"[a-z0-9]+", normalized_keyword):
        pattern = rf"\b{re.escape(normalized_keyword)}\b"
        return re.search(pattern, normalized_text) is not None

    return normalized_keyword in normalized_text


def _contains_negative(text, keyword):
    """Busca palabras negativas con una excepcion para Semi Senior."""
    normalized_text = _normalize(text)
    normalized_keyword = _normalize(keyword)

    if normalized_keyword == "senior":
        normalized_text = normalized_text.replace("semi senior", "")

    return _contains_keyword(normalized_text, normalized_keyword)


def _mentioned_years(text):
    """Extrae menciones simples como '1 año', '2 años' o '5 anios'."""
    normalized_text = _normalize(text)
    matches = re.findall(r"\b(\d+)\s*(?:ano|anos|anio|anios)\b", normalized_text)
    return [int(match) for match in matches]


def _has_low_experience(text, max_years):
    years = _mentioned_years(text)
    return bool(years) and min(years) <= max_years


def _has_high_experience(text, min_years):
    years = _mentioned_years(text)
    return any(year > min_years for year in years)


def _clamp_score(score, rules):
    minimum = rules.get("puntaje_minimo", 0)
    maximum = rules.get("puntaje_maximo", 100)
    return max(minimum, min(maximum, score))


def _is_generic_alert_title(title):
    """Detecta titulos que parecen alertas generales, no ofertas concretas."""
    normalized_title = _normalize(title)
    generic_phrases = [
        "alerta general de empleo",
        "nuevas vacantes",
        "nuevas ofertas",
        "te buscan para nuevos empleos",
        "empresas necesitan talento",
    ]

    return any(phrase in normalized_title for phrase in generic_phrases)


def _score_email_type(email_type, rules):
    """Calcula ajuste por tipo de correo parseado."""
    if email_type == "job_alert":
        return 0, "Tipo de correo: alerta de empleo"
    if email_type == "application_update":
        return rules.get("tipo_application_update", -25), (
            "Tipo de correo: seguimiento de postulacion"
        )
    if email_type == "generic_notification":
        return rules.get("tipo_generic_notification", -35), (
            "Tipo de correo: notificacion general"
        )

    return 0, ""


def _score_link(link, rules):
    """Premia links que parecen ir a una oferta concreta o a una lista util."""
    normalized_link = _normalize(link)
    concrete_patterns = [
        "o_detail",
        "oferta-de-trabajo-de",
        "linkedin.com/jobs/view",
        "jobs/view",
    ]
    list_patterns = [
        "o_grid",
        "jobs/search",
        "search",
        "ofertas-de-trabajo/?",
        "q=",
    ]

    if any(pattern in normalized_link for pattern in concrete_patterns):
        return rules.get("link_oferta_concreta", 15), (
            "Link parece apuntar a una oferta concreta"
        )
    if any(pattern in normalized_link for pattern in list_patterns):
        return rules.get("link_lista_ofertas", 3), (
            "Link parece apuntar a una lista de ofertas"
        )

    return 0, ""


def calculate_score(job, config):
    """Calcula el puntaje de una oferta y explica los motivos."""
    score = 0
    reasons = []
    rules = config.get("reglas_puntaje", {})
    text = _job_text(job)
    email_type = job.get("email_type", "")

    email_type_score, email_type_reason = _score_email_type(email_type, rules)
    score += email_type_score
    if email_type_reason:
        reasons.append(email_type_reason)

    if _is_generic_alert_title(job.get("title", "")):
        score += rules.get("titulo_generico_alerta", -10)
        reasons.append("Titulo generico de alerta")

    link_score, link_reason = _score_link(job.get("link", ""), rules)
    score += link_score
    if link_reason:
        reasons.append(link_reason)

    for technology in config.get("tecnologias_fuertes", []):
        if _contains_keyword(text, technology):
            score += rules.get("tecnologia_fuerte", 0)
            reasons.append(f"Coincide con {technology}")

    for modality in config.get("modalidades_preferidas", []):
        if _contains_keyword(job.get("modality", ""), modality):
            score += rules.get("modalidad_preferida", 0)
            reasons.append(f"Modalidad preferida: {modality}")
            break

    for location in config.get("ubicaciones_preferidas", []):
        if _contains_keyword(job.get("location", ""), location):
            score += rules.get("ubicacion_preferida", 0)
            reasons.append(f"Ubicacion preferida: {location}")
            break

    for level in config.get("niveles_preferidos", []):
        if _contains_keyword(text, level):
            score += rules.get("nivel_preferido", 0)
            reasons.append(f"Nivel compatible: {level}")
            break

    conditional = config.get("tecnologias_condicionales", {})
    compatible_levels = conditional.get("niveles_compatibles", [])
    non_priority_levels = conditional.get("niveles_no_prioritarios", [])
    low_experience_limit = conditional.get("experiencia_baja_max_anios", 3)
    high_experience_limit = conditional.get("experiencia_no_prioritaria_mayor_a_anios", 3)

    has_compatible_level = any(_contains_keyword(text, level) for level in compatible_levels)
    has_non_priority_level = any(_contains_keyword(text, level) for level in non_priority_levels)
    has_low_experience = _has_low_experience(text, low_experience_limit)
    has_high_experience = _has_high_experience(text, high_experience_limit)

    for technology in conditional.get("nombres", []):
        if not _contains_keyword(text, technology):
            continue

        if has_compatible_level or has_low_experience:
            score += rules.get("tecnologia_condicional_compatible", 0)
            reasons.append(f"Tecnologia condicional compatible: {technology}")
        elif has_non_priority_level or has_high_experience:
            score += rules.get("tecnologia_condicional_no_prioritaria", 0)
            reasons.append(f"Tecnologia condicional no priorizada por nivel: {technology}")
        else:
            reasons.append(f"Tecnologia condicional detectada sin nivel claro: {technology}")

    for negative_word in config.get("palabras_negativas", []):
        if _contains_negative(text, negative_word):
            score += rules.get("palabra_negativa", 0)
            reasons.append(f"Resta por palabra negativa: {negative_word}")

    if email_type == "application_update":
        score = min(score, rules.get("max_application_update", 5))
        reasons.append("Seguimiento de postulacion: no compite como oferta nueva")

    return {
        "score": _clamp_score(score, rules),
        "reasons": reasons,
    }
