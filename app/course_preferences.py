from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .database import connect, initialize


@dataclass(frozen=True)
class CoursePreferences:
    course_id: int
    language: str
    citation_style: str
    tone: str
    target_length: str
    teacher_requirements: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def generation_instructions(self) -> str:
        details = [
            f"作业语言：{self.language}",
            f"引用格式：{self.citation_style}",
            f"写作语气：{self.tone}",
        ]
        if self.target_length:
            details.append(f"目标篇幅：{self.target_length}")
        if self.teacher_requirements:
            details.append(f"老师要求：{self.teacher_requirements}")
        return "；".join(details)


class CoursePreferencesNotFoundError(LookupError):
    pass


class CoursePreferencesRepository:
    def __init__(self, database: Path | None = None) -> None:
        self.database = database
        initialize(database)

    def get(self, course_id: int) -> CoursePreferences:
        with closing(connect(self.database)) as connection:
            course = connection.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
            if course is None:
                raise CoursePreferencesNotFoundError(f"课程 {course_id} 不存在")
            row = connection.execute(
                "SELECT * FROM course_preferences WHERE course_id = ?", (course_id,)
            ).fetchone()
        if row is not None:
            return CoursePreferences(**dict(row))
        return CoursePreferences(
            course_id,
            "中文",
            "课程资料编号引用",
            "清楚、正式的大学作业语气",
            "",
            "",
            "",
        )

    def save(
        self,
        course_id: int,
        language: str,
        citation_style: str,
        tone: str,
        target_length: str,
        teacher_requirements: str,
    ) -> CoursePreferences:
        values = [language.strip(), citation_style.strip(), tone.strip()]
        if any(not value for value in values):
            raise ValueError("语言、引用格式和写作语气不能为空")
        now = datetime.now(timezone.utc).isoformat()
        with closing(connect(self.database)) as connection:
            course = connection.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
            if course is None:
                raise CoursePreferencesNotFoundError(f"课程 {course_id} 不存在")
            connection.execute(
                """
                INSERT INTO course_preferences (
                    course_id, language, citation_style, tone, target_length,
                    teacher_requirements, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id) DO UPDATE SET
                    language = excluded.language,
                    citation_style = excluded.citation_style,
                    tone = excluded.tone,
                    target_length = excluded.target_length,
                    teacher_requirements = excluded.teacher_requirements,
                    updated_at = excluded.updated_at
                """,
                (course_id, *values, target_length.strip(), teacher_requirements.strip(), now),
            )
            connection.commit()
        return self.get(course_id)
