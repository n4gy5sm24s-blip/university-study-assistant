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
_EXHIBIT_REFERENCE = re.compile(
    r"(?<![A-Za-z])exhibit\s*([0-9]+)\s*[.．·_-]\s*([0-9]+)(?![0-9])",
    re.IGNORECASE,
)
_SLIDE_REFERENCE = re.compile(
    r"(?:(?:ch(?:apter)?\s*0*([0-9]+)|第\s*0*([0-9]+)\s*章)\s*(?:的|[-_:/\\ ]*)?)?"
    r"(?:第\s*0*([0-9]+)\s*(?:张|页)(?:\s*(?:ppt|幻灯片))?|"
    r"(?:slide|ppt)\s*0*([0-9]+))",
    re.IGNORECASE,
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
    english_words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query)
    english_phrase = " ".join(english_words)
    terms = [english_phrase, *english_words, compact]
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
        exhibit = _EXHIBIT_REFERENCE.search(clean_query)
        if exhibit:
            reference = f"exhibit {exhibit.group(1)}.{exhibit.group(2)}"
            return self._search_exact_reference(course_id, reference, safe_limit)
        slide = _SLIDE_REFERENCE.search(clean_query)
        if slide:
            chapter = next((value for value in slide.groups()[:2] if value), None)
            slide_number = next(value for value in slide.groups()[2:] if value)
            return self._search_exact_slide(
                course_id, int(slide_number), int(chapter) if chapter else None, safe_limit
            )
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

    def _search_exact_reference(
        self, course_id: int, reference: str, limit: int
    ) -> list[SearchResult]:
        pattern = f"%{reference.lower()}%"
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
                  AND (lower(c.section_title) LIKE ? OR lower(c.content) LIKE ?)
                ORDER BY
                  CASE WHEN lower(c.section_title) LIKE '%text alternative%' THEN 0 ELSE 1 END,
                  length(c.content) DESC,
                  c.id
                LIMIT ?
                """,
                (course_id, pattern, pattern, limit),
            ).fetchall()
        return [SearchResult(**dict(row)) for row in rows]

    def _search_exact_slide(
        self, course_id: int, slide_number: int, chapter: int | None, limit: int
    ) -> list[SearchResult]:
        title_pattern = f"%第 {slide_number} 张：%"
        chapter_patterns = (
            [f"%ch{chapter:02d}%", f"%ch{chapter}%", f"%chapter{chapter:02d}%", f"%chapter{chapter}%"]
            if chapter is not None
            else []
        )
        with connect(self.database) as connection:
            course = connection.execute(
                "SELECT id FROM courses WHERE id = ?", (course_id,)
            ).fetchone()
            if course is None:
                raise SearchCourseNotFoundError(f"课程 {course_id} 不存在")
            parameters: list[object] = [course_id, title_pattern]
            chapter_filter = ""
            if chapter_patterns:
                chapter_filter = " AND (" + " OR ".join(
                    "lower(d.filename) LIKE ?" for _ in chapter_patterns
                ) + ")"
                parameters.extend(chapter_patterns)
            parameters.append(limit)
            rows = connection.execute(
                f"""
                SELECT c.id AS chunk_id, c.document_id, d.filename,
                       c.section_title, c.sequence, c.content, 0.0 AS score
                FROM chunks c
                JOIN source_documents d ON d.id = c.document_id
                WHERE c.course_id = ? AND c.section_title LIKE ?
                {chapter_filter}
                ORDER BY c.id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [SearchResult(**dict(row)) for row in rows]

    def expand_course_context(
        self,
        course_id: int,
        anchors: list[SearchResult],
        radius: int = 2,
        limit: int = 7,
    ) -> list[SearchResult]:
        """Add nearby slides and chapter objectives around the strongest result."""
        if not anchors:
            return []
        safe_limit = max(1, min(limit, 10))
        selected: list[SearchResult] = []
        seen: set[int] = set()

        def add(result: SearchResult) -> None:
            if result.chunk_id not in seen and len(selected) < safe_limit:
                selected.append(result)
                seen.add(result.chunk_id)

        # Exact references can have both an image slide and a later text alternative.
        for anchor in anchors[:2]:
            add(anchor)

        primary_document = anchors[0].document_id
        anchor_sequences = [
            item.sequence for item in anchors[:2] if item.document_id == primary_document
        ]
        with connect(self.database) as connection:
            placeholders = " OR ".join(
                "(c.sequence BETWEEN ? AND ?)" for _ in anchor_sequences
            )
            parameters: list[object] = [course_id, primary_document]
            for sequence in anchor_sequences:
                parameters.extend([max(0, sequence - radius), sequence + radius])
            rows = connection.execute(
                f"""
                SELECT c.id AS chunk_id, c.document_id, d.filename,
                       c.section_title, c.sequence, c.content, 0.0 AS score
                FROM chunks c
                JOIN source_documents d ON d.id = c.document_id
                WHERE c.course_id = ? AND c.document_id = ? AND ({placeholders})
                ORDER BY c.sequence
                """,
                parameters,
            ).fetchall()
            objective = connection.execute(
                """
                SELECT c.id AS chunk_id, c.document_id, d.filename,
                       c.section_title, c.sequence, c.content, 0.0 AS score
                FROM chunks c
                JOIN source_documents d ON d.id = c.document_id
                WHERE c.course_id = ? AND c.document_id = ?
                  AND lower(c.section_title) LIKE '%learning objectives%'
                ORDER BY c.sequence LIMIT 1
                """,
                (course_id, primary_document),
            ).fetchone()
        for row in rows:
            add(SearchResult(**dict(row)))
        if objective is not None:
            add(SearchResult(**dict(objective)))
        return selected

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


