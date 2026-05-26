"""Analisis opcional de ofertas usando OpenAI.

Este modulo complementa el scoring local. No reemplaza scorer.py, no guarda
resultados y no automatiza postulaciones.
"""

import json
import os

import requests


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

DEFAULT_ANALYSIS = {
    "summary": "",
    "fit_level": "bajo",
    "fit_score": 0,
    "estimated_seniority": "",
    "detected_stack": [],
    "positive_signals": [],
    "red_flags": [],
    "missing_info": [],
    "recommendation": "",
    "apply_priority": "baja",
}


ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "fit_level": {
            "type": "string",
            "enum": ["alto", "medio", "bajo"],
        },
        "fit_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "estimated_seniority": {"type": "string"},
        "detected_stack": {
            "type": "array",
            "items": {"type": "string"},
        },
        "positive_signals": {
            "type": "array",
            "items": {"type": "string"},
        },
        "red_flags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "missing_info": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommendation": {"type": "string"},
        "apply_priority": {
            "type": "string",
            "enum": ["alta", "media", "baja"],
        },
    },
    "required": [
        "summary",
        "fit_level",
        "fit_score",
        "estimated_seniority",
        "detected_stack",
        "positive_signals",
        "red_flags",
        "missing_info",
        "recommendation",
        "apply_priority",
    ],
}


def load_openai_credentials():
    """Carga OPENAI_API_KEY desde .env sin imprimir secretos."""
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Falta instalar python-dotenv. Ejecuta: pip install -r requirements.txt"
        ) from exc

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("Falta configurar OPENAI_API_KEY en el archivo .env local.")

    return {
        "OPENAI_API_KEY": api_key,
    }


def _short_text(value, max_length):
    """Recorta texto para evitar prompts grandes."""
    text = " ".join(str(value or "").split())

    if len(text) <= max_length:
        return text

    return text[:max_length].rstrip() + "..."


def build_job_analysis_prompt(job, config):
    """Construye un prompt pequeno para analizar una oferta ya filtrada."""
    settings = config.get("ai_settings", {})
    include_raw_description = settings.get("include_raw_description", False)
    reasons = job.get("reasons", [])

    lines = [
        "Analiza esta oferta laboral ya filtrada por job-watcher.",
        "No inventes datos que no aparezcan en la oferta.",
        "No escribas CV, no generes postulaciones y no automatices acciones.",
        "",
        "Perfil objetivo:",
        "- Desarrollador Junior o Semi Senior.",
        "- Stack fuerte: Angular, TypeScript, JavaScript, .NET, C#, ASP.NET Core.",
        "- Tambien valen Node.js, SQL Server, PostgreSQL, API REST, JWT y Git.",
        "- Python y PL/SQL solo son alta compatibilidad si el rol es Junior, Entry Level o Trainee.",
        "- Evitar Senior, Lead, Architect y Manager.",
        "- Evitar roles no dev como Sales, Marketing, Legal, Recruiter o Product Manager.",
        "- Evitar AI/ML, Data Scientist, DevOps y Security salvo que sea muy junior y compatible.",
        "",
        f"Titulo: {job.get('title', '')}",
        f"Empresa: {job.get('company', '')}",
        f"Portal: {job.get('portal', '')}",
        f"Ubicacion: {job.get('location', '')}",
        f"Modalidad local: {job.get('modality', '')}",
        f"Score local: {job.get('score', 0)}",
        f"Motivos locales: {', '.join(map(str, reasons[:8]))}",
        f"Fuente: {job.get('source_type', job.get('email_type', ''))}",
    ]

    if include_raw_description:
        lines.append(
            "Descripcion: "
            + _short_text(job.get("description", ""), max_length=1800)
        )
    else:
        lines.append(
            "Descripcion: omitida por configuracion para reducir costo y contexto."
        )

    lines.extend(
        [
            "",
            "Devuelve solo JSON con:",
            "- summary",
            "- fit_level: alto, medio o bajo",
            "- fit_score: entero de 0 a 100",
            "- estimated_seniority",
            "- detected_stack",
            "- positive_signals",
            "- red_flags",
            "- missing_info",
            "- recommendation",
            "- apply_priority: alta, media o baja",
        ]
    )

    return "\n".join(lines)


def _extract_output_text(response_data):
    """Extrae texto de una respuesta de OpenAI de forma tolerante."""
    if response_data.get("output_text"):
        return response_data["output_text"]

    for item in response_data.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")

    return ""


def _parse_analysis(text):
    """Convierte JSON de la IA al formato esperado."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_analysis(
            "Respuesta IA no interpretable",
            "Revisar manualmente: OpenAI no devolvio JSON valido.",
        )

    if not isinstance(data, dict):
        return _fallback_analysis(
            "Respuesta IA con formato inesperado",
            "Revisar manualmente: OpenAI no devolvio un objeto JSON.",
        )

    return _normalize_analysis(data)


def _ensure_list(value):
    """Normaliza campos que deben ser listas para evitar formatos raros."""
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value]

    return [str(value)]


def _normalize_enum(value, allowed_values, default):
    """Garantiza que un texto quede dentro de valores esperados."""
    normalized = str(value or "").strip().lower()
    if normalized in allowed_values:
        return normalized

    return default


def _normalize_fit_score(value):
    """Convierte fit_score a entero entre 0 y 100."""
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0

    return max(0, min(score, 100))


def _normalize_analysis(data):
    """Completa y valida el contrato estructurado del analisis IA."""
    analysis = dict(DEFAULT_ANALYSIS)
    analysis.update(data)
    analysis["summary"] = str(analysis.get("summary", "") or "")
    analysis["fit_level"] = _normalize_enum(
        analysis.get("fit_level"),
        ["alto", "medio", "bajo"],
        "bajo",
    )
    analysis["fit_score"] = _normalize_fit_score(analysis.get("fit_score"))
    analysis["estimated_seniority"] = str(
        analysis.get("estimated_seniority", "") or ""
    )
    analysis["detected_stack"] = _ensure_list(analysis.get("detected_stack"))
    analysis["positive_signals"] = _ensure_list(analysis.get("positive_signals"))
    analysis["red_flags"] = _ensure_list(analysis.get("red_flags"))
    analysis["missing_info"] = _ensure_list(analysis.get("missing_info"))
    analysis["recommendation"] = str(analysis.get("recommendation", "") or "")
    analysis["apply_priority"] = _normalize_enum(
        analysis.get("apply_priority"),
        ["alta", "media", "baja"],
        "baja",
    )
    return analysis


def _fallback_analysis(red_flag, recommendation):
    """Devuelve un analisis seguro cuando la IA no responde como esperamos."""
    analysis = dict(DEFAULT_ANALYSIS)
    analysis["red_flags"] = [red_flag]
    analysis["missing_info"] = ["Analisis IA estructurado no disponible"]
    analysis["recommendation"] = recommendation
    return analysis


def analyze_job_with_openai(job, config):
    """Analiza una oferta individual usando OpenAI si esta configurado."""
    settings = config.get("ai_settings", {})
    credentials = load_openai_credentials()
    prompt = build_job_analysis_prompt(job, config)
    payload = {
        "model": settings.get("model", "gpt-4.1-mini"),
        "instructions": (
            "Eres un asistente de analisis de ofertas laborales. "
            "Responde en espanol, con criterio conservador y solo en JSON."
        ),
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "job_analysis",
                "schema": ANALYSIS_SCHEMA,
                "strict": True,
            }
        },
        "max_output_tokens": 700,
    }

    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {credentials['OPENAI_API_KEY']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        response_data = response.json()
    except requests.RequestException as exc:
        raise RuntimeError("Fallo la llamada a OpenAI.") from exc
    except ValueError as exc:
        raise RuntimeError("OpenAI devolvio una respuesta no interpretable.") from exc

    output_text = _extract_output_text(response_data)
    if not output_text:
        return _fallback_analysis(
            "Respuesta IA vacia",
            "Revisar manualmente: OpenAI no devolvio texto de analisis.",
        )

    return _parse_analysis(output_text)


def analyze_jobs_batch(jobs, config):
    """Analiza un lote pequeno de ofertas ya filtradas por score."""
    settings = config.get("ai_settings", {})

    if not settings.get("enabled", False):
        return []

    min_score = int(settings.get("min_score", 20))
    max_jobs = int(settings.get("max_jobs_per_cycle", 3))
    candidates = [
        job for job in jobs if int(job.get("score", 0) or 0) >= min_score
    ][:max_jobs]
    results = []

    for job in candidates:
        results.append(
            {
                "job": job,
                "analysis": analyze_job_with_openai(job, config),
            }
        )

    return results
