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
        job.get("description", ""),
        job.get("location", ""),
        job.get("modality", ""),
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


def calculate_score(job, config):
    """Calcula el puntaje de una oferta y explica los motivos."""
    score = 0
    reasons = []
    rules = config.get("reglas_puntaje", {})
    text = _job_text(job)

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

    return {
        "score": _clamp_score(score, rules),
        "reasons": reasons,
    }
