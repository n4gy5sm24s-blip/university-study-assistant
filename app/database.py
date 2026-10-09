from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path


def database_path() -> Path:
    configured = os.environ.get("STUDY_ASSISTANT_DB")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "study_assistant.db"


def connect(path: Path | None = None) -> sqlite3.Connection:
    selected = path or database_path()
    selected.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(selected)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(path: Path | None = None) -> None:
    with closing(connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK(length(trim(name)) > 0),
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                media_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                UNIQUE(course_id, content_hash)
            )
            """
        )
        connection.commit()
