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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
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
                description, link, score, reasons
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(link) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                portal = excluded.portal,
                location = excluded.location,
                modality = excluded.modality,
                description = excluded.description,
                score = excluded.score,
                reasons = excluded.reasons
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
            ),
        )


def get_all_jobs():
    """Retorna todas las ofertas guardadas, ordenadas por puntaje."""
    with _connect() as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                id, title, company, portal, location, modality,
                description, link, score, reasons, created_at
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
