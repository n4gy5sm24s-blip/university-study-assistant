from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing

from .database import connect, initialize


@dataclass(frozen=True)
class Course:
    id: int
    name: str
    description: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class CourseNotFoundError(LookupError):
    pass


class CourseRepository:
    def __init__(self, database: Path | None = None) -> None:
        self.database = database
        initialize(database)

    def create(self, name: str, description: str = "") -> Course:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("课程名称不能为空")
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(connect(self.database)) as connection:
            cursor = connection.execute(
                "INSERT INTO courses (name, description, created_at) VALUES (?, ?, ?)",
                (clean_name, description.strip(), created_at),
            )
            course_id = int(cursor.lastrowid)
            connection.commit()
        return Course(course_id, clean_name, description.strip(), created_at)

    def list_all(self) -> list[Course]:
        with closing(connect(self.database)) as connection:
            rows = connection.execute(
                "SELECT id, name, description, created_at FROM courses ORDER BY id DESC"
            ).fetchall()
        return [Course(**dict(row)) for row in rows]

    def delete(self, course_id: int) -> None:
        with closing(connect(self.database)) as connection:
            cursor = connection.execute("DELETE FROM courses WHERE id = ?", (course_id,))
            if cursor.rowcount == 0:
                raise CourseNotFoundError(f"课程 {course_id} 不存在")
            connection.commit()
