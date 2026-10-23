from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .database import connect
from .documents import DocumentRepository
from .retrieval import RetrievalRepository


@dataclass(frozen=True)
class CourseProfile:
    document_count: int
    chunk_count: int
    topics: list[str]
    material_status: str
    summary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class CourseProfileService:
    def __init__(self, database: Path | None = None) -> None:
        self.documents = DocumentRepository(database)
        self.retrieval = RetrievalRepository(database)

    def build(self, course_id: int) -> CourseProfile:
        documents = self.documents.list_for_course(course_id)
        chunks = self.retrieval.list_course_chunks(course_id, limit=100)
        with connect(self.retrieval.database) as connection:
            chunk_count = int(connection.execute(
                "SELECT COUNT(*) FROM chunks WHERE course_id = ?", (course_id,)
            ).fetchone()[0])
        labels = [chunk.section_title.strip() or chunk.filename for chunk in chunks]
        topics = [label for label, _ in Counter(labels).most_common(8)]
        if not documents:
            return CourseProfile(0, 0, [], "empty", "还没有课程资料，先上传老师的 PPTX。")
        if len(topics) < 3:
            status = "limited"
            summary = "资料已经可以使用，但主题覆盖较少；写作业时可能需要补充教材页面。"
        else:
            status = "ready"
            summary = f"已从 {len(documents)} 份资料中整理出 {len(topics)} 个主要主题，可以开始检索和写作。"
        return CourseProfile(len(documents), chunk_count, topics, status, summary)
