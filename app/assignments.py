from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from .database import connect, initialize


@dataclass(frozen=True)
class Assignment:
    id: int
    course_id: int
    title: str
    prompt: str
    draft: str
    final_text: str
    citations: list[dict[str, object]]
    status: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AssignmentNotFoundError(LookupError):
    pass


class AssignmentValidationError(ValueError):
    pass


class AssignmentRepository:
    def __init__(self, database: Path | None = None) -> None:
        self.database = database
        initialize(database)

    def create(
        self,
        course_id: int,
        title: str,
        prompt: str,
        draft: str,
        citations: list[dict[str, object]],
    ) -> Assignment:
        clean_title = title.strip()[:120]
        clean_prompt = prompt.strip()
        if not clean_title or not clean_prompt:
            raise AssignmentValidationError("作业标题和题目不能为空")
        now = datetime.now(timezone.utc).isoformat()
        with closing(connect(self.database)) as connection:
            course = connection.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
            if course is None:
                raise AssignmentNotFoundError(f"课程 {course_id} 不存在")
            cursor = connection.execute(
                """
                INSERT INTO assignments (
                    course_id, title, prompt, draft, final_text, citations_json,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?)
                """,
                (course_id, clean_title, clean_prompt, draft, draft, json.dumps(citations, ensure_ascii=False), now, now),
            )
            connection.commit()
        return self.get(course_id, int(cursor.lastrowid))

    def list_for_course(self, course_id: int) -> list[Assignment]:
        with closing(connect(self.database)) as connection:
            rows = connection.execute(
                "SELECT * FROM assignments WHERE course_id = ? ORDER BY updated_at DESC, id DESC",
                (course_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, course_id: int, assignment_id: int) -> Assignment:
        with closing(connect(self.database)) as connection:
            row = connection.execute(
                "SELECT * FROM assignments WHERE id = ? AND course_id = ?",
                (assignment_id, course_id),
            ).fetchone()
        if row is None:
            raise AssignmentNotFoundError(f"作业项目 {assignment_id} 不存在")
        return self._from_row(row)

    def update(self, course_id: int, assignment_id: int, final_text: str, status: str) -> Assignment:
        clean_text = final_text.strip()
        if not clean_text:
            raise AssignmentValidationError("最终稿不能为空")
        if status not in {"draft", "complete"}:
            raise AssignmentValidationError("未知的作业状态")
        now = datetime.now(timezone.utc).isoformat()
        with closing(connect(self.database)) as connection:
            cursor = connection.execute(
                "UPDATE assignments SET final_text = ?, status = ?, updated_at = ? WHERE id = ? AND course_id = ?",
                (clean_text, status, now, assignment_id, course_id),
            )
            if cursor.rowcount == 0:
                raise AssignmentNotFoundError(f"作业项目 {assignment_id} 不存在")
            connection.commit()
        return self.get(course_id, assignment_id)

    @staticmethod
    def _from_row(row: object) -> Assignment:
        values = dict(row)
        values["citations"] = json.loads(values.pop("citations_json"))
        return Assignment(**values)
