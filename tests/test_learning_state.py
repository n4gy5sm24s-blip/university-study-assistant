from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.courses import CourseRepository
from app.documents import DocumentRepository
from app.learning_state import LearningRecordNotFoundError, LearningStateRepository
from app.retrieval import RetrievalRepository


class LearningStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.courses = CourseRepository(self.database)
        self.documents = DocumentRepository(self.database, self.root / "uploads")
        self.learning = LearningStateRepository(self.database)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_questions_accumulate_and_user_status_persists(self) -> None:
        course = self.courses.create("管理学")
        document = self.documents.create(
            course.id, "chapter4.md", "# Business Strategy\n低成本与差异化战略。"
        )
        chunk = RetrievalRepository(self.database).search(course.id, "差异化战略")[0]
        first = self.learning.record_interaction(
            course.id, document.id, chunk.sequence, chunk.section_title, "讲讲业务战略"
        )
        self.assertEqual(first.interaction_count, 1)
        self.learning.update_status(course.id, first.id, "review")
        second = self.learning.record_interaction(
            course.id, document.id, chunk.sequence, chunk.section_title, "低成本有什么区别"
        )
        self.assertEqual(second.interaction_count, 2)
        self.assertEqual(second.status, "review")
        summary = self.learning.summary(course.id)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["review"], 1)

    def test_course_deletion_removes_learning_records(self) -> None:
        course = self.courses.create("管理学")
        document = self.documents.create(course.id, "lesson.md", "# 战略\n战略决定方向。")
        self.learning.record_interaction(course.id, document.id, 0, "战略", "什么是战略")
        self.courses.delete(course.id)
        with self.assertRaises(LearningRecordNotFoundError):
            self.learning.summary(course.id)

    def test_rejects_unknown_status(self) -> None:
        course = self.courses.create("管理学")
        document = self.documents.create(course.id, "lesson.md", "# 战略\n战略决定方向。")
        record = self.learning.record_interaction(course.id, document.id, 0, "战略", "什么是战略")
        with self.assertRaises(ValueError):
            self.learning.update_status(course.id, record.id, "unknown")


if __name__ == "__main__":
    unittest.main()
