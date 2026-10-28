from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .database import connect, initialize


@dataclass(frozen=True)
class LearningRecord:
    id: int
    course_id: int
    document_id: int
    sequence: int
    topic: str
    status: str
    interaction_count: int
    last_question: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class LearningRecordNotFoundError(LookupError):
    pass


class LearningStateRepository:
    def __init__(self, database: Path | None = None) -> None:
        self.database = database
        initialize(database)

    def record_interaction(
        self,
        course_id: int,
        document_id: int,
        sequence: int,
        topic: str,
        question: str,
    ) -> LearningRecord:
        now = datetime.now(timezone.utc).isoformat()
        with connect(self.database) as connection:
            connection.execute(
                """
                INSERT INTO learning_records (
                    course_id, document_id, sequence, topic, status,
                    interaction_count, last_question, updated_at
                ) VALUES (?, ?, ?, ?, 'learning', 1, ?, ?)
                ON CONFLICT(course_id, document_id, sequence) DO UPDATE SET
                    topic = excluded.topic,
                    interaction_count = learning_records.interaction_count + 1,
                    last_question = excluded.last_question,
                    updated_at = excluded.updated_at
                """,
                (course_id, document_id, sequence, topic.strip(), question.strip(), now),
            )
            connection.commit()
            row = connection.execute(
                """
                SELECT * FROM learning_records
                WHERE course_id = ? AND document_id = ? AND sequence = ?
                """,
                (course_id, document_id, sequence),
            ).fetchone()
        return LearningRecord(**dict(row))

    def update_status(self, course_id: int, record_id: int, status: str) -> LearningRecord:
        if status not in {"learning", "mastered", "review"}:
            raise ValueError("学习状态只允许 learning、mastered 或 review")
        now = datetime.now(timezone.utc).isoformat()
        with connect(self.database) as connection:
            cursor = connection.execute(
                """
                UPDATE learning_records SET status = ?, updated_at = ?
                WHERE id = ? AND course_id = ?
                """,
                (status, now, record_id, course_id),
            )
            if cursor.rowcount == 0:
                raise LearningRecordNotFoundError("没有找到这条学习记录")
            connection.commit()
            row = connection.execute(
                "SELECT * FROM learning_records WHERE id = ?", (record_id,)
            ).fetchone()
        return LearningRecord(**dict(row))

    def summary(self, course_id: int) -> dict[str, object]:
        with connect(self.database) as connection:
            course = connection.execute(
                "SELECT id FROM courses WHERE id = ?", (course_id,)
            ).fetchone()
            if course is None:
                raise LearningRecordNotFoundError(f"课程 {course_id} 不存在")
            rows = connection.execute(
                """
                SELECT * FROM learning_records
                WHERE course_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (course_id,),
            ).fetchall()
        records = [LearningRecord(**dict(row)) for row in rows]
        return {
            "total": len(records),
            "mastered": sum(item.status == "mastered" for item in records),
            "review": sum(item.status == "review" for item in records),
            "learning": sum(item.status == "learning" for item in records),
            "records": [item.to_dict() for item in records[:12]],
        }
