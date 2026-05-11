"""Modulo inicial para leer metadatos de correos mediante IMAP.

Este archivo queda preparado para una fase futura. No esta conectado a
main.py y no se ejecuta automaticamente.
"""

import imaplib
import os
from datetime import datetime, timedelta
from email import message_from_bytes
from email.header import decode_header


def _to_bool(value):
    """Convierte valores de entorno comunes a booleano."""
    return str(value).strip().lower() in {"true", "1", "yes", "y", "si"}


def _contains_any(text, keywords):
    """Busca palabras clave sin diferenciar mayusculas y minusculas."""
    normalized_text = str(text or "").lower()
    return any(str(keyword).lower() in normalized_text for keyword in keywords)


def _decode_subject(subject):
    """Decodifica asuntos que pueden venir en formatos MIME."""
    if not subject:
        return ""

    try:
        decoded_parts = []
        for fragment, charset in decode_header(subject):
            if isinstance(fragment, bytes):
                decoded_parts.append(_decode_bytes(fragment, charset))
            else:
                decoded_parts.append(_repair_text(fragment))

        return "".join(decoded_parts).strip()
    except (LookupError, UnicodeDecodeError, ValueError):
        return _repair_text(subject)


def _repair_text(text):
    """Corrige algunos artefactos comunes de codificacion."""
    repaired = str(text or "")

    # Caso comun: texto UTF-8 leido como latin-1/cp1252, por ejemplo prÃ³ximo.
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

    return repaired.replace("\x00", "").strip()


def _decode_bytes(payload, charset=None):
    """Decodifica bytes probando varias codificaciones seguras."""
    encodings = []
    for encoding in (charset, "utf-8", "cp1252", "latin-1"):
        if encoding and encoding not in encodings:
            encodings.append(encoding)

    candidates = []
    for encoding in encodings:
        try:
            candidates.append(payload.decode(encoding))
        except (LookupError, UnicodeDecodeError):
            continue

    if candidates:
        best_candidate = min(candidates, key=lambda value: value.count("\ufffd"))
        return _repair_text(best_candidate)

    return _repair_text(payload.decode("utf-8", errors="replace"))


def _decode_payload(part):
    """Decodifica una parte del correo usando su charset cuando exista."""
    payload = part.get_payload(decode=True)
    charset = part.get_content_charset()

    if payload is None:
        raw_payload = part.get_payload()
        return _repair_text(raw_payload) if isinstance(raw_payload, str) else ""

    return _decode_bytes(payload, charset)


def _extract_bodies(message):
    """Extrae la primera parte util en texto plano y HTML."""
    text_body = ""
    html_body = ""

    if message.is_multipart():
        parts = message.walk()
    else:
        parts = [message]

    for part in parts:
        if part.is_multipart():
            continue

        disposition = str(part.get("Content-Disposition", "")).lower()
        if "attachment" in disposition:
            continue

        content_type = part.get_content_type()
        decoded_payload = _decode_payload(part)

        if content_type == "text/plain" and not text_body:
            text_body = decoded_payload
        elif content_type == "text/html" and not html_body:
            html_body = decoded_payload

        if text_body and html_body:
            break

    return text_body, html_body


def load_email_credentials():
    """Carga credenciales IMAP desde un archivo .env local.

    El archivo .env no debe subirse al repositorio. Esta funcion no imprime
    contrasenas ni datos sensibles.
    """
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Falta instalar python-dotenv. Ejecuta: pip install -r requirements.txt"
        ) from exc

    load_dotenv()

    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")

    if not email_user or not email_password:
        raise ValueError(
            "Falta configurar EMAIL_USER o EMAIL_PASSWORD en el archivo .env local."
        )

    return {
        "EMAIL_USER": email_user,
        "EMAIL_PASSWORD": email_password,
        "EMAIL_IMAP_SERVER": os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com"),
        "EMAIL_IMAP_PORT": int(os.getenv("EMAIL_IMAP_PORT", "993")),
        "EMAIL_USE_SSL": _to_bool(os.getenv("EMAIL_USE_SSL", "true")),
    }


def create_imap_connection(credentials):
    """Crea una conexion IMAP y hace login con las credenciales recibidas."""
    server = credentials["EMAIL_IMAP_SERVER"]
    port = credentials["EMAIL_IMAP_PORT"]
    use_ssl = credentials["EMAIL_USE_SSL"]

    try:
        if use_ssl:
            connection = imaplib.IMAP4_SSL(server, port)
        else:
            connection = imaplib.IMAP4(server, port)

        connection.login(credentials["EMAIL_USER"], credentials["EMAIL_PASSWORD"])
        return connection
    except imaplib.IMAP4.error as exc:
        raise ConnectionError(
            "No fue posible iniciar sesion en el servidor IMAP. "
            "Revisa usuario, metodo de autenticacion y configuracion IMAP."
        ) from exc
    except OSError as exc:
        raise ConnectionError(
            "No fue posible conectar con el servidor IMAP. "
            "Revisa servidor, puerto y conexion a internet."
        ) from exc


def close_connection(connection):
    """Cierra una conexion IMAP de forma segura."""
    if connection is None:
        return

    try:
        connection.logout()
    except (imaplib.IMAP4.error, OSError, AttributeError):
        # La conexion puede estar cerrada o en un estado invalido.
        pass


def build_since_date(days_back):
    """Devuelve una fecha compatible con IMAP, por ejemplo 01-Jan-2026."""
    since_date = datetime.now() - timedelta(days=int(days_back))
    return since_date.strftime("%d-%b-%Y")


def search_recent_email_ids(connection, folder, days_back, max_emails):
    """Busca IDs de correos recientes en una carpeta IMAP."""
    status, _ = connection.select(folder)
    if status != "OK":
        raise RuntimeError(f"No se pudo seleccionar la carpeta IMAP: {folder}")

    since_date = build_since_date(days_back)
    status, data = connection.search(None, "SINCE", since_date)
    if status != "OK" or not data:
        return []

    email_ids = data[0].split()
    email_ids = list(reversed(email_ids))
    return email_ids[: int(max_emails)]


def read_email_metadata(connection, email_id):
    """Lee metadatos basicos de un correo sin procesar el cuerpo."""
    status, data = connection.fetch(email_id, "(BODY.PEEK[HEADER])")
    if status != "OK" or not data:
        raise RuntimeError(f"No se pudieron leer metadatos del correo {email_id!r}")

    raw_message = data[0][1]
    message = message_from_bytes(raw_message)

    return {
        "subject": _decode_subject(message.get("Subject", "")),
        "sender": message.get("From", ""),
        "date": message.get("Date", ""),
        "message_id": email_id.decode() if isinstance(email_id, bytes) else email_id,
    }


def read_email_content(connection, email_id):
    """Lee un correo completo y retorna asunto, remitente y cuerpos utiles."""
    try:
        status, data = connection.fetch(email_id, "(RFC822)")
    except imaplib.IMAP4.error as exc:
        raise RuntimeError(f"No se pudo leer el correo {email_id!r} por IMAP.") from exc

    if status != "OK" or not data:
        raise RuntimeError(f"No se pudo obtener el contenido del correo {email_id!r}.")

    raw_message = None
    for item in data:
        if isinstance(item, tuple) and len(item) > 1:
            raw_message = item[1]
            break

    if not raw_message:
        raise RuntimeError(f"El correo {email_id!r} no tiene contenido legible.")

    try:
        message = message_from_bytes(raw_message)
        text_body, html_body = _extract_bodies(message)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"No se pudo interpretar el correo {email_id!r}.") from exc

    return {
        "message_id": email_id.decode() if isinstance(email_id, bytes) else email_id,
        "subject": _decode_subject(message.get("Subject", "")),
        "sender": message.get("From", ""),
        "date": message.get("Date", ""),
        "text_body": text_body,
        "html_body": html_body,
    }


def read_recent_email_metadata(settings):
    """Lee metadatos recientes usando la configuracion email_settings.

    Esta funcion es de alto nivel, pero no se llama automaticamente desde
    main.py. Solo debe usarse manualmente cuando se quiera probar IMAP.
    """
    credentials = load_email_credentials()
    connection = None
    emails = []

    try:
        connection = create_imap_connection(credentials)
        for folder in settings.get("folders", ["INBOX"]):
            email_ids = search_recent_email_ids(
                connection,
                folder,
                settings.get("days_back", 1),
                settings.get("max_emails", 20),
            )

            for email_id in email_ids:
                metadata = read_email_metadata(connection, email_id)
                metadata["folder"] = folder
                emails.append(metadata)
    finally:
        close_connection(connection)

    return emails


def read_recent_filtered_emails(settings):
    """Lee cuerpos solo de correos recientes que pasen el filtro de metadatos."""
    credentials = load_email_credentials()
    connection = None
    emails = []
    max_emails = int(settings.get("max_emails", 20))

    try:
        connection = create_imap_connection(credentials)

        for folder in settings.get("folders", ["INBOX"]):
            if len(emails) >= max_emails:
                break

            email_ids = search_recent_email_ids(
                connection,
                folder,
                settings.get("days_back", 1),
                max_emails,
            )

            metadata_list = []
            for email_id in email_ids:
                metadata = read_email_metadata(connection, email_id)
                metadata["folder"] = folder
                metadata["_email_id"] = email_id
                metadata_list.append(metadata)

            filtered_metadata = filter_email_metadata(metadata_list, settings)

            for metadata in filtered_metadata:
                if len(emails) >= max_emails:
                    break

                content = read_email_content(connection, metadata["_email_id"])
                content["folder"] = folder
                emails.append(content)
    finally:
        close_connection(connection)

    return emails


def filter_email_metadata(emails, settings):
    """Filtra metadatos para quedarse con posibles alertas laborales."""
    subject_keywords = settings.get("subject_keywords", [])
    sender_keywords = settings.get("sender_keywords", [])
    ignored_keywords = settings.get("ignored_keywords", [])
    filtered = []

    for email_metadata in emails:
        subject = email_metadata.get("subject", "")
        sender = email_metadata.get("sender", "")
        combined_text = f"{subject} {sender}"

        if _contains_any(combined_text, ignored_keywords):
            continue

        matches_subject = _contains_any(subject, subject_keywords)
        matches_sender = _contains_any(sender, sender_keywords)

        if matches_subject or matches_sender:
            filtered.append(email_metadata)

    return filtered
