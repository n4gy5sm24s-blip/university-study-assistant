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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                section_title TEXT NOT NULL DEFAULT '',
                sequence INTEGER NOT NULL,
                content TEXT NOT NULL CHECK(length(trim(content)) > 0),
                FOREIGN KEY (document_id) REFERENCES source_documents(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                UNIQUE(document_id, sequence)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                prompt TEXT NOT NULL CHECK(length(trim(prompt)) > 0),
                draft TEXT NOT NULL DEFAULT '',
                final_text TEXT NOT NULL DEFAULT '',
                citations_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS course_preferences (
                course_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT '中文',
                citation_style TEXT NOT NULL DEFAULT '课程资料编号引用',
                tone TEXT NOT NULL DEFAULT '清楚、正式的大学作业语气',
                target_length TEXT NOT NULL DEFAULT '',
                teacher_requirements TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                sequence INTEGER NOT NULL,
                topic TEXT NOT NULL CHECK(length(trim(topic)) > 0),
                status TEXT NOT NULL DEFAULT 'learning'
                    CHECK(status IN ('learning', 'mastered', 'review')),
                interaction_count INTEGER NOT NULL DEFAULT 1,
                last_question TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES source_documents(id) ON DELETE CASCADE,
                UNIQUE(course_id, document_id, sequence)
            )
            """
        )
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunk_search USING fts5(
                chunk_id UNINDEXED,
                course_id UNINDEXED,
                content,
                tokenize='trigram'
            )
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS chunks_after_insert
            AFTER INSERT ON chunks BEGIN
                INSERT INTO chunk_search (chunk_id, course_id, content)
                VALUES (new.id, new.course_id, new.content);
            END
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS chunks_after_delete
            AFTER DELETE ON chunks BEGIN
                DELETE FROM chunk_search WHERE chunk_id = old.id;
            END
            """
        )
        connection.commit()
