"""Modulo inicial para leer metadatos de correos mediante IMAP.

Este archivo queda preparado para una fase futura. No esta conectado a
main.py y no se ejecuta automaticamente.
"""

import imaplib
import os
from datetime import datetime, timedelta
from email import message_from_bytes
from email.header import decode_header, make_header


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
        return str(make_header(decode_header(subject)))
    except (LookupError, UnicodeDecodeError, ValueError):
        return subject


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
