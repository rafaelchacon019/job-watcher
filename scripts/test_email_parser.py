"""Prueba manual del parser inicial de correos.

Este script lee correos filtrados solo si email_settings.enabled es true.
No guarda en SQLite, no genera CSV y no muestra cuerpos completos.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.email_parser import parse_emails_to_jobs
from src.email_reader import read_recent_filtered_emails


def load_email_settings():
    """Carga email_settings desde config.yaml."""
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Falta instalar PyYAML. Ejecuta: pip install -r requirements.txt"
        ) from exc

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}

    return config.get("email_settings", {})


def show_jobs(jobs):
    """Muestra maximo 10 posibles ofertas sin imprimir cuerpos de correo."""
    print("Posibles ofertas extraidas:")

    for index, job in enumerate(jobs[:10], start=1):
        print(f"{index}. Type: {job.get('email_type', '')}")
        print(f"   Title: {job.get('title', '')}")
        print(f"   Company: {job.get('company', '')}")
        print(f"   Portal: {job.get('portal', '')}")
        print(f"   Location: {job.get('location', '')}")
        print(f"   Modality: {job.get('modality', '')}")
        print(f"   Link: {job.get('link', '')}")


def main():
    """Ejecuta una prueba manual y controlada del parser."""
    print("Prueba manual del parser inicial de correos.")

    try:
        email_settings = load_email_settings()

        if not email_settings.get("enabled", False):
            print(
                "La lectura de correo esta desactivada en config.yaml "
                "(email_settings.enabled: false)."
            )
            print("Activa temporalmente enabled: true solo cuando quieras probar.")
            return

        emails = read_recent_filtered_emails(email_settings)
        jobs = parse_emails_to_jobs(emails)

        print(f"Correos filtrados leidos: {len(emails)}")
        print(f"Posibles ofertas extraidas: {len(jobs)}")
        show_jobs(jobs)

    except ValueError as exc:
        print(f"Configuracion incompleta: {exc}")
    except ConnectionError as exc:
        print(f"Error de conexion o autenticacion IMAP: {exc}")
    except RuntimeError as exc:
        print(f"Error durante la prueba del parser: {exc}")
    except OSError as exc:
        print(f"Error de acceso a archivos o red: {exc}")


if __name__ == "__main__":
    main()
