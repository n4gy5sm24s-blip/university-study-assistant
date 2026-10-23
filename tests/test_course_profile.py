from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.course_profile import CourseProfileService
from app.courses import CourseRepository
from app.documents import DocumentRepository


class CourseProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.course = CourseRepository(self.database).create("管理学", "测试课程")
        self.documents = DocumentRepository(self.database, self.root / "uploads")
        self.service = CourseProfileService(self.database)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_empty_course_profile(self) -> None:
        profile = self.service.build(self.course.id)
        self.assertEqual(profile.document_count, 0)
        self.assertEqual(profile.material_status, "empty")

    def test_profile_extracts_section_topics(self) -> None:
        self.documents.create(
            self.course.id,
            "week1.md",
            "# 领导力\n领导力帮助团队协作。\n\n# 激励\n激励影响员工行为。\n\n# 决策\n决策需要比较方案。",
        )
        profile = self.service.build(self.course.id)
        self.assertEqual(profile.document_count, 1)
        self.assertEqual(profile.material_status, "ready")
        self.assertIn("领导力", profile.topics)


if __name__ == "__main__":
    unittest.main()
