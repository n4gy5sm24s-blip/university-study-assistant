from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.assignments import AssignmentRepository
from app.courses import CourseRepository


class AssignmentRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.course = CourseRepository(self.database).create("管理学")
        self.assignments = AssignmentRepository(self.database)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_create_list_and_update_assignment(self) -> None:
        created = self.assignments.create(
            self.course.id,
            "领导力案例分析",
            "分析案例中的领导方式",
            "初稿内容",
            [{"filename": "week1.pptx", "excerpt": "领导力资料"}],
        )
        self.assertEqual(self.assignments.list_for_course(self.course.id)[0].id, created.id)
        updated = self.assignments.update(self.course.id, created.id, "修改后的最终稿", "complete")
        self.assertEqual(updated.final_text, "修改后的最终稿")
        self.assertEqual(updated.status, "complete")


if __name__ == "__main__":
    unittest.main()
