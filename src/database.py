"""Funciones simples para guardar ofertas en SQLite."""

import json
import sqlite3
from pathlib import Path

from src.deduplication import build_job_fingerprint


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
                fingerprint TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_column(connection, "jobs", "email_type", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "jobs", "fingerprint", "TEXT NOT NULL DEFAULT ''")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(fingerprint)"
        )


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
    fingerprint = job.get("fingerprint") or build_job_fingerprint(job)

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO jobs (
                title, company, portal, location, modality,
                description, link, score, reasons, email_type, fingerprint
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(link) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                portal = excluded.portal,
                location = excluded.location,
                modality = excluded.modality,
                description = excluded.description,
                score = excluded.score,
                reasons = excluded.reasons,
                email_type = excluded.email_type,
                fingerprint = excluded.fingerprint
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
                fingerprint,
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
    fingerprint = job.get("fingerprint") or build_job_fingerprint(job)

    with _connect() as connection:
        existing_by_link = connection.execute(
            "SELECT id FROM jobs WHERE link = ?",
            (job["link"],),
        ).fetchone()

        if existing_by_link:
            _update_existing_job(
                connection,
                existing_by_link[0],
                job,
                reasons_json,
                email_type,
                fingerprint,
            )
            return False

        if fingerprint:
            existing_by_fingerprint = connection.execute(
                """
                SELECT id FROM jobs
                WHERE fingerprint = ?
                LIMIT 1
                """,
                (fingerprint,),
            ).fetchone()

            if existing_by_fingerprint:
                _update_existing_job(
                    connection,
                    existing_by_fingerprint[0],
                    job,
                    reasons_json,
                    email_type,
                    fingerprint,
                )
                return False

        cursor = connection.execute(
            """
            INSERT INTO jobs (
                title, company, portal, location, modality,
                description, link, score, reasons, email_type, fingerprint
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                fingerprint,
            ),
        )

        if cursor.rowcount == 1:
            return True

        return False


def _update_existing_job(connection, job_id, job, reasons_json, email_type, fingerprint):
    """Actualiza datos utiles de una oferta ya existente."""
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
            END,
            fingerprint = CASE
                WHEN (fingerprint IS NULL OR fingerprint = '') AND ? != ''
                THEN ?
                ELSE fingerprint
            END
        WHERE id = ?
        """,
        (
            job["score"],
            reasons_json,
            email_type,
            email_type,
            fingerprint,
            fingerprint,
            job_id,
        ),
    )


def job_exists_by_fingerprint(fingerprint, current_link=""):
    """Indica si ya existe una oferta con la misma huella y otro link."""
    if not fingerprint:
        return False

    with _connect() as connection:
        row = connection.execute(
            """
            SELECT id FROM jobs
            WHERE fingerprint = ? AND link != ?
            LIMIT 1
            """,
            (fingerprint, current_link),
        ).fetchone()

    return row is not None


def get_all_jobs():
    """Retorna todas las ofertas guardadas, ordenadas por puntaje."""
    with _connect() as connection:
        connection.row_factory = sqlite3.Row
        columns = connection.execute("PRAGMA table_info(jobs)").fetchall()
        column_names = {column["name"] for column in columns}
        email_type_field = "email_type" if "email_type" in column_names else "'' AS email_type"
        fingerprint_field = (
            "fingerprint" if "fingerprint" in column_names else "'' AS fingerprint"
        )

        rows = connection.execute(
            f"""
            SELECT
                id, title, company, portal, location, modality,
                description, link, score, reasons, {email_type_field},
                {fingerprint_field}, created_at
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
