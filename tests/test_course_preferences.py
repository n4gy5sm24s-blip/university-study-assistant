from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.course_preferences import CoursePreferencesRepository
from app.courses import CourseRepository


class CoursePreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.course = CourseRepository(self.database).create("管理学")
        self.preferences = CoursePreferencesRepository(self.database)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_defaults_and_saved_preferences(self) -> None:
        self.assertEqual(self.preferences.get(self.course.id).language, "中文")
        saved = self.preferences.save(
            self.course.id,
            "英文",
            "APA 7th",
            "正式、简洁",
            "800-1000 words",
            "必须结合课程案例",
        )
        self.assertEqual(saved.citation_style, "APA 7th")
        self.assertIn("课程案例", saved.generation_instructions())


if __name__ == "__main__":
    unittest.main()
