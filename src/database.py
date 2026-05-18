"""Funciones simples para guardar ofertas en SQLite."""

import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "jobs.db"


def _connect():
    """Crea una conexion a la base local."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Crea la tabla de ofertas si todavia no existe."""
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                portal TEXT NOT NULL,
                location TEXT NOT NULL,
                modality TEXT NOT NULL,
                description TEXT NOT NULL,
                link TEXT NOT NULL UNIQUE,
                score INTEGER NOT NULL,
                reasons TEXT NOT NULL,
                email_type TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_column(connection, "jobs", "email_type", "TEXT NOT NULL DEFAULT ''")


def _ensure_column(connection, table_name, column_name, column_definition):
    """Agrega una columna si la base fue creada en una fase anterior."""
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    column_names = {column[1] for column in columns}

    if column_name not in column_names:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def save_job(job):
    """Guarda una oferta y actualiza sus datos si el link ya existe."""
    reasons = job.get("reasons", [])
    reasons_json = json.dumps(reasons, ensure_ascii=False)

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO jobs (
                title, company, portal, location, modality,
                description, link, score, reasons, email_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(link) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                portal = excluded.portal,
                location = excluded.location,
                modality = excluded.modality,
                description = excluded.description,
                score = excluded.score,
                reasons = excluded.reasons,
                email_type = excluded.email_type
            """,
            (
                job["title"],
                job["company"],
                job["portal"],
                job["location"],
                job["modality"],
                job["description"],
                job["link"],
                job["score"],
                reasons_json,
                job.get("email_type", ""),
            ),
        )


def save_job_if_not_exists(job):
    """Guarda una oferta solo si su link no existe todavia.

    Si el link ya existe, actualiza puntaje, motivos y email_type cuando falte.
    Retorna True si inserto una fila nueva y False si el link ya existia.
    """
    reasons = job.get("reasons", [])
    reasons_json = json.dumps(reasons, ensure_ascii=False)
    email_type = job.get("email_type", "")

    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO jobs (
                title, company, portal, location, modality,
                description, link, score, reasons, email_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job["title"],
                job["company"],
                job["portal"],
                job["location"],
                job["modality"],
                job["description"],
                job["link"],
                job["score"],
                reasons_json,
                email_type,
            ),
        )

        if cursor.rowcount == 1:
            return True

        connection.execute(
            """
            UPDATE jobs
            SET
                score = ?,
                reasons = ?,
                email_type = CASE
                    WHEN (email_type IS NULL OR email_type = '') AND ? != ''
                    THEN ?
                    ELSE email_type
                END
            WHERE link = ?
            """,
            (
                job["score"],
                reasons_json,
                email_type,
                email_type,
                job["link"],
            ),
        )

        return False


def get_all_jobs():
    """Retorna todas las ofertas guardadas, ordenadas por puntaje."""
    with _connect() as connection:
        connection.row_factory = sqlite3.Row
        columns = connection.execute("PRAGMA table_info(jobs)").fetchall()
        column_names = {column["name"] for column in columns}
        email_type_field = "email_type" if "email_type" in column_names else "'' AS email_type"

        rows = connection.execute(
            f"""
            SELECT
                id, title, company, portal, location, modality,
                description, link, score, reasons, {email_type_field}, created_at
            FROM jobs
            ORDER BY score DESC, created_at DESC
            """
        ).fetchall()

    jobs = []
    for row in rows:
        job = dict(row)
        job["reasons"] = json.loads(job["reasons"])
        jobs.append(job)

    return jobs
