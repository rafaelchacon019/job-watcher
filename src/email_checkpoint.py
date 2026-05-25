"""Checkpoint local para evitar reprocesar correos ya revisados."""

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = {
    "last_run_at": None,
    "processed_message_ids": [],
}


def _resolve_checkpoint_path(path):
    """Convierte una ruta relativa en ruta absoluta dentro del proyecto."""
    checkpoint_path = Path(path or "data/email_checkpoint.json")

    if checkpoint_path.is_absolute():
        return checkpoint_path

    return PROJECT_ROOT / checkpoint_path


def _empty_checkpoint():
    """Retorna una copia limpia del estado inicial."""
    return {
        "last_run_at": DEFAULT_CHECKPOINT["last_run_at"],
        "processed_message_ids": list(DEFAULT_CHECKPOINT["processed_message_ids"]),
    }


def load_checkpoint(path):
    """Lee el checkpoint local si existe.

    Si el archivo no existe o no se puede interpretar, se retorna un estado
    vacio para que el worker pueda continuar sin romperse.
    """
    checkpoint_path = _resolve_checkpoint_path(path)

    if not checkpoint_path.exists():
        return _empty_checkpoint()

    try:
        with checkpoint_path.open("r", encoding="utf-8") as checkpoint_file:
            data = json.load(checkpoint_file)
    except (OSError, json.JSONDecodeError):
        return _empty_checkpoint()

    return {
        "last_run_at": data.get("last_run_at"),
        "processed_message_ids": list(data.get("processed_message_ids", [])),
    }


def filter_unprocessed_emails(emails, checkpoint):
    """Deja solo correos cuyo message_id no este en el checkpoint."""
    processed_ids = {
        str(message_id)
        for message_id in checkpoint.get("processed_message_ids", [])
        if message_id
    }
    new_emails = []

    for email_data in emails:
        message_id = email_data.get("message_id")

        if message_id and str(message_id) in processed_ids:
            continue

        new_emails.append(email_data)

    return new_emails


def update_checkpoint(checkpoint, processed_emails, max_processed_ids=500):
    """Actualiza fecha y ultimos IDs procesados sin crecer indefinidamente."""
    known_ids = [
        str(message_id)
        for message_id in checkpoint.get("processed_message_ids", [])
        if message_id
    ]

    for email_data in processed_emails:
        message_id = email_data.get("message_id")
        if not message_id:
            continue

        message_id = str(message_id)
        if message_id in known_ids:
            known_ids.remove(message_id)

        known_ids.append(message_id)

    try:
        limit = int(max_processed_ids or 500)
    except (TypeError, ValueError):
        limit = 500

    return {
        "last_run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "processed_message_ids": known_ids[-limit:],
    }


def save_checkpoint(checkpoint, path):
    """Guarda el checkpoint local en JSON."""
    checkpoint_path = _resolve_checkpoint_path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    with checkpoint_path.open("w", encoding="utf-8") as checkpoint_file:
        json.dump(checkpoint, checkpoint_file, ensure_ascii=False, indent=2)
        checkpoint_file.write("\n")
