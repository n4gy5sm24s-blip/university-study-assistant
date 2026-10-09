from pathlib import Path
import unittest
from uuid import uuid4

from app.courses import CourseNotFoundError, CourseRepository


class CourseRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_directory = Path(__file__).parent / ".tmp"
        temp_directory.mkdir(exist_ok=True)
        self.database = temp_directory / f"{uuid4().hex}.db"
        self.repository = CourseRepository(self.database)

    def tearDown(self) -> None:
        self.database.unlink(missing_ok=True)

    def test_create_and_list_course(self) -> None:
        created = self.repository.create("管理学", "专业基础课")
        courses = self.repository.list_all()
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0], created)

    def test_rejects_blank_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "不能为空"):
            self.repository.create("   ")

    def test_delete_course(self) -> None:
        course = self.repository.create("经济学")
        self.repository.delete(course.id)
        self.assertEqual(self.repository.list_all(), [])

    def test_delete_missing_course(self) -> None:
        with self.assertRaises(CourseNotFoundError):
            self.repository.delete(999)


if __name__ == "__main__":
    unittest.main()
