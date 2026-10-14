from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import sqlite3

from .database import connect, initialize


MAX_CHUNK_CHARACTERS = 800
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
_QUERY_NOISE = re.compile(
    r"请问|麻烦|帮我|解释一下|介绍一下|告诉我|什么是|是什么意思|为什么|怎么|如何|"
    r"请|呢|吗|？|\?|！|!|，|,|。|\.|：|:|；|;|\s+"
)


@dataclass(frozen=True)
class ChunkDraft:
    section_title: str
    sequence: int
    content: str


@dataclass(frozen=True)
class SearchResult:
    chunk_id: int
    document_id: int
    filename: str
    section_title: str
    sequence: int
    content: str
    score: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class SearchValidationError(ValueError):
    pass


class SearchCourseNotFoundError(LookupError):
    pass


def build_fts_query(query: str) -> str:
    compact = _QUERY_NOISE.sub("", query.strip())
    if len(compact) < 3:
        compact = re.sub(r"\s+", "", query.strip())
    terms = [compact]
    if len(compact) > 3:
        terms.extend(compact[index : index + 3] for index in range(len(compact) - 2))
    unique_terms = list(dict.fromkeys(term for term in terms if len(term) >= 3))
    return " OR ".join(
        f'"{term.replace(chr(34), chr(34) * 2)}"' for term in unique_terms
    )


def _pack_paragraphs(
    paragraphs: list[str], section_title: str, start_sequence: int
) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    current = ""
    sequence = start_sequence

    def emit(text: str) -> None:
        nonlocal sequence
        clean = text.strip()
        if clean:
            chunks.append(ChunkDraft(section_title, sequence, clean))
            sequence += 1

    for paragraph in paragraphs:
        clean = paragraph.strip()
        if not clean:
            continue
        while len(clean) > MAX_CHUNK_CHARACTERS:
            if current:
                emit(current)
                current = ""
            split_at = clean.rfind("。", 0, MAX_CHUNK_CHARACTERS)
            if split_at < MAX_CHUNK_CHARACTERS // 2:
                split_at = MAX_CHUNK_CHARACTERS
            else:
                split_at += 1
            emit(clean[:split_at])
            clean = clean[split_at:].strip()
        candidate = f"{current}\n\n{clean}".strip() if current else clean
        if len(candidate) <= MAX_CHUNK_CHARACTERS:
            current = candidate
        else:
            emit(current)
            current = clean
    emit(current)
    return chunks


def split_text(content: str, media_type: str) -> list[ChunkDraft]:
    sections: list[tuple[str, list[str]]] = []
    title = ""
    paragraphs: list[str] = []
    paragraph_lines: list[str] = []

    def finish_paragraph() -> None:
        if paragraph_lines:
            paragraphs.append("\n".join(paragraph_lines).strip())
            paragraph_lines.clear()

    def finish_section() -> None:
        finish_paragraph()
        if paragraphs:
            sections.append((title, paragraphs.copy()))
            paragraphs.clear()

    for line in content.splitlines():
        heading = _MARKDOWN_HEADING.match(line) if media_type == "text/markdown" else None
        if heading:
            finish_section()
            title = heading.group(1).strip()
        elif line.strip():
            paragraph_lines.append(line.strip())
        else:
            finish_paragraph()
    finish_section()

    chunks: list[ChunkDraft] = []
    for section_title, section_paragraphs in sections:
        chunks.extend(_pack_paragraphs(section_paragraphs, section_title, len(chunks)))
    return chunks


def index_document(
    connection: sqlite3.Connection,
    document_id: int,
    course_id: int,
    content: str,
    media_type: str,
) -> None:
    for chunk in split_text(content, media_type):
        connection.execute(
            """
            INSERT INTO chunks (document_id, course_id, section_title, sequence, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, course_id, chunk.section_title, chunk.sequence, chunk.content),
        )


class RetrievalRepository:
    def __init__(self, database: Path | None = None) -> None:
        self.database = database
        initialize(database)

    def search(self, course_id: int, query: str, limit: int = 10) -> list[SearchResult]:
        clean_query = query.strip()
        if len(clean_query) < 3:
            raise SearchValidationError("搜索词至少需要 3 个字符")
        safe_limit = max(1, min(limit, 20))
        fts_query = build_fts_query(clean_query)
        with connect(self.database) as connection:
            course = connection.execute(
                "SELECT id FROM courses WHERE id = ?", (course_id,)
            ).fetchone()
            if course is None:
                raise SearchCourseNotFoundError(f"课程 {course_id} 不存在")
            rows = connection.execute(
                """
                SELECT c.id AS chunk_id, c.document_id, d.filename,
                       c.section_title, c.sequence, c.content,
                       bm25(chunk_search) AS score
                FROM chunk_search
                JOIN chunks c ON c.id = chunk_search.chunk_id
                JOIN source_documents d ON d.id = c.document_id
                WHERE chunk_search MATCH ? AND chunk_search.course_id = ?
                ORDER BY score, c.id
                LIMIT ?
                """,
                (fts_query, course_id, safe_limit),
            ).fetchall()
        return [SearchResult(**dict(row)) for row in rows]

    def list_course_chunks(self, course_id: int, limit: int = 50) -> list[SearchResult]:
        safe_limit = max(1, min(limit, 100))
        with connect(self.database) as connection:
            course = connection.execute(
                "SELECT id FROM courses WHERE id = ?", (course_id,)
            ).fetchone()
            if course is None:
                raise SearchCourseNotFoundError(f"课程 {course_id} 不存在")
            rows = connection.execute(
                """
                SELECT c.id AS chunk_id, c.document_id, d.filename,
                       c.section_title, c.sequence, c.content, 0.0 AS score
                FROM chunks c
                JOIN source_documents d ON d.id = c.document_id
                WHERE c.course_id = ?
                ORDER BY d.id, c.sequence
                LIMIT ?
                """,
                (course_id, safe_limit),
            ).fetchall()
        return [SearchResult(**dict(row)) for row in rows]


