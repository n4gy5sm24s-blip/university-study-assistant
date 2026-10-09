from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.courses import CourseRepository
from app.documents import (
    CourseNotFoundError,
    DocumentRepository,
    DocumentValidationError,
    DuplicateDocumentError,
)


class DocumentRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.storage = self.root / "uploads"
        self.courses = CourseRepository(self.database)
        self.documents = DocumentRepository(self.database, self.storage)
        self.course = self.courses.create("测试课程")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_upload_and_list_text_document(self) -> None:
        created = self.documents.create(
            self.course.id, "lesson.md", "# 第一课\n这是自制测试资料。"
        )
        listed = self.documents.list_for_course(self.course.id)
        self.assertEqual(listed, [created])
        self.assertEqual(created.status, "ready")
        self.assertEqual(len(list(self.storage.rglob("*.md"))), 1)

    def test_rejects_unsupported_and_empty_documents(self) -> None:
        with self.assertRaises(DocumentValidationError):
            self.documents.create(self.course.id, "lesson.pdf", "内容")
        with self.assertRaises(DocumentValidationError):
            self.documents.create(self.course.id, "lesson.txt", "   ")

    def test_rejects_duplicate_content_in_same_course(self) -> None:
        self.documents.create(self.course.id, "one.txt", "相同内容")
        with self.assertRaises(DuplicateDocumentError):
            self.documents.create(self.course.id, "two.txt", "相同内容")

    def test_rejects_missing_course(self) -> None:
        with self.assertRaises(CourseNotFoundError):
            self.documents.create(999, "lesson.txt", "测试内容")

    def test_delete_removes_database_record_and_file(self) -> None:
        created = self.documents.create(
            self.course.id, "lesson.txt", "将被删除的测试内容"
        )
        self.documents.delete(self.course.id, created.id)
        self.assertEqual(self.documents.list_for_course(self.course.id), [])
        self.assertEqual(list(self.storage.rglob("*.txt")), [])


if __name__ == "__main__":
    unittest.main()
