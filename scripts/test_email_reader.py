"""Prueba manual y controlada del lector IMAP.

Este script solo lee metadatos basicos de correos. No guarda informacion en
SQLite, no genera CSV y no extrae ofertas laborales.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.email_reader import filter_email_metadata, read_recent_email_metadata


def load_email_settings():
    """Carga la seccion email_settings desde config.yaml."""
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Falta instalar PyYAML. Ejecuta: pip install -r requirements.txt"
        ) from exc

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}

    return config.get("email_settings", {})


def show_results(filtered_emails):
    """Muestra una lista corta de posibles alertas laborales."""
    print("Resultados filtrados:")

    for index, email_metadata in enumerate(filtered_emails[:10], start=1):
        print(f"{index}. Subject: {email_metadata.get('subject', '')}")
        print(f"   Sender: {email_metadata.get('sender', '')}")
        print(f"   Date: {email_metadata.get('date', '')}")


def main():
    """Ejecuta la prueba manual solo si email_settings.enabled es true."""
    print("Prueba manual de lectura de metadatos por IMAP.")

    try:
        email_settings = load_email_settings()

        if not email_settings.get("enabled", False):
            print(
                "La lectura de correo esta desactivada en config.yaml "
                "(email_settings.enabled: false)."
            )
            print("Activa temporalmente enabled: true solo cuando quieras probar.")
            return

        emails = read_recent_email_metadata(email_settings)
        filtered_emails = filter_email_metadata(emails, email_settings)

        print(f"Correos recientes leidos: {len(emails)}")
        print(f"Posibles alertas laborales encontradas: {len(filtered_emails)}")
        show_results(filtered_emails)

    except ValueError as exc:
        print(f"Configuracion incompleta: {exc}")
    except ConnectionError as exc:
        print(f"Error de conexion o autenticacion IMAP: {exc}")
    except RuntimeError as exc:
        print(f"Error durante la prueba IMAP: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos o red: {exc}")


if __name__ == "__main__":
    main()
